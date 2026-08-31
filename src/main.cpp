#define TINYGLTF_IMPLEMENTATION
#define STB_IMAGE_WRITE_IMPLEMENTATION
#define STB_IMAGE_IMPLEMENTATION
#ifdef _MSC_VER
#	define STBI_MSC_SECURE_CRT
#endif
#include <tiny_gltf.h>
#undef TINYGLTF_IMPLEMENTATION
#undef STB_IMAGE_WRITE_IMPLEMENTATION
#undef STB_IMAGE_IMPLEMENTATION

#include <gflags/gflags.h>

#include "app.h"

DEFINE_string(scene, "", "Path to the scene file.");
DEFINE_bool(ignore_point_lights, false, "Ignore point lights in the scene.");
DEFINE_uint64(light_seed, 0, "Seed for the procedurally generated point-light set (used when the scene defines no lights).");
DEFINE_string(camera_position, "", "Fixed camera position 'x,y,z'. Requires --camera_look_at. Locks camera control.");
DEFINE_string(camera_look_at, "", "Fixed camera look-at target 'x,y,z'. Requires --camera_position. Locks camera control.");
DEFINE_bool(benchmark, false, "Enable benchmark mode: run warmup frames, then record frame times and exit.");
DEFINE_uint64(warmup_frames, 300, "Number of warmup frames before measurement starts (benchmark mode).");
DEFINE_uint64(measure_frames, 1000, "Number of frames to measure (benchmark mode).");
DEFINE_string(frame_times_csv, "frame_times.csv", "Output CSV path for per-frame time records (benchmark mode).");
DEFINE_int64(screenshot_frame, -1, "Measured-frame index at which to capture a PNG screenshot (benchmark mode, -1 disables).");
DEFINE_string(screenshot_path, "screenshot.png", "Output PNG path for the benchmark screenshot.");
DEFINE_bool(screenshot_now, false, "Capture a screenshot immediately after warmup and exit (interactive shortcut: F9).");
DEFINE_bool(temporal_reuse, true, "Enable temporal reservoir reuse.");
DEFINE_int64(temporal_clamp, 20, "Temporal reservoir sample-count clamp multiplier.");
DEFINE_int64(spatial_iterations, 1, "Biased spatial reuse iteration count (0 disables spatial reuse).");
DEFINE_int64(initial_samples_log2, 5, "Base-two exponent of the initial light-sample count (5 = 32 samples).");
DEFINE_string(visibility, "hardware", "Visibility path: 'disabled', 'software' or 'hardware'.");
DEFINE_int64(device_index, -1, "Index of the discrete GPU to use (-1 selects the last suitable discrete GPU).");
DEFINE_string(window_size, "", "Window/framebuffer size 'widthxheight', e.g. --window_size=1920x1080.");

static bool _parseVec3(const std::string& text, nvmath::vec3f& out) {
	float x, y, z;
	if (sscanf(text.c_str(), "%f,%f,%f", &x, &y, &z) != 3) {
		return false;
	}
	out = nvmath::vec3f(x, y, z);
	return true;
}

int main(int argc, char **argv) {
	gflags::ParseCommandLineFlags(&argc, &argv, true);

	BenchmarkConfig benchmark;
	benchmark.enabled = FLAGS_benchmark || FLAGS_screenshot_now;
	benchmark.warmupFrames = FLAGS_warmup_frames;
	benchmark.measureFrames = FLAGS_measure_frames;
	benchmark.frameTimesCsv = FLAGS_frame_times_csv;
	benchmark.screenshotPath = FLAGS_screenshot_path;
	if (FLAGS_screenshot_frame >= 0) {
		benchmark.screenshotFrame = static_cast<uint64_t>(FLAGS_screenshot_frame);
	} else if (FLAGS_screenshot_now) {
		// Capture on the first measured frame (right after warmup).
		benchmark.screenshotFrame = 1;
		if (!FLAGS_benchmark) {
			// Quick capture-and-exit mode when benchmark was not requested.
			benchmark.measureFrames = 1;
		}
	}

	std::optional<CameraPreset> preset;
	if (!FLAGS_camera_position.empty() || !FLAGS_camera_look_at.empty()) {
		if (FLAGS_camera_position.empty() || FLAGS_camera_look_at.empty()) {
			std::cerr << "--camera_position and --camera_look_at must be specified together.\n";
			return 1;
		}
		CameraPreset p;
		if (!_parseVec3(FLAGS_camera_position, p.position) || !_parseVec3(FLAGS_camera_look_at, p.lookAt)) {
			std::cerr << "Camera arguments must use the form 'x,y,z', e.g. --camera_position=5.0,4.0,10.0\n";
			return 1;
		}
		preset = p;
	}

	ExperimentConfig experiment;
	experiment.temporalReuse = FLAGS_temporal_reuse;
	experiment.temporalClamp = static_cast<int>(FLAGS_temporal_clamp);
	experiment.spatialIterations = static_cast<int>(FLAGS_spatial_iterations);
	experiment.initialSamplesLog2 = static_cast<int>(FLAGS_initial_samples_log2);
	experiment.deviceIndex = static_cast<int>(FLAGS_device_index);
	if (FLAGS_visibility == "disabled") {
		experiment.visibility = VisibilityTestMethod::disabled;
	} else if (FLAGS_visibility == "software") {
		experiment.visibility = VisibilityTestMethod::software;
	} else if (FLAGS_visibility == "hardware") {
		experiment.visibility = VisibilityTestMethod::hardware;
	} else {
		std::cerr << "--visibility must be one of: disabled, software, hardware\n";
		return 1;
	}
	if (!FLAGS_window_size.empty()) {
		unsigned w, h;
		if (sscanf(FLAGS_window_size.c_str(), "%ux%u", &w, &h) != 2 || w == 0 || h == 0) {
			std::cerr << "--window_size must use the form 'widthxheight', e.g. --window_size=1920x1080\n";
			return 1;
		}
		experiment.windowSize = vk::Extent2D(w, h);
	}

	App app(FLAGS_scene, FLAGS_ignore_point_lights, static_cast<unsigned>(FLAGS_light_seed), preset, benchmark, experiment);
	app.mainLoop();
	return 0;
}
