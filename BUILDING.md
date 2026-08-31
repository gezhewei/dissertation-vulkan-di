# Visual Studio 2026 构建说明

本项目使用 CMake 生成 Visual Studio 2026 x64 工程。仓库根目录中的 `CMakePresets.json` 已配置好生成器。

## 在 Visual Studio 中

1. 使用 Visual Studio 2026 打开仓库根目录（`文件 -> 打开 -> 文件夹`）。
2. 选择配置预设 `Visual Studio 2026 x64`。
3. 将启动目标设为 `ReSTIR.exe`，选择 Debug 或 Release 后生成并运行。

调试参数默认加载仓库中随附的 `scenes/Sponza/glTF/Sponza.gltf`。

## 命令行

在“Developer PowerShell for VS 2026”中执行：

```powershell
cmake --preset vs2026-x64
cmake --build --preset vs2026-release
```

输出程序位于 `build/vs2026/bin/Release/ReSTIR.exe`，编译后的 SPIR-V 着色器会自动复制到同目录的 `shaders` 文件夹。

## 论文渲染配置

当前版本采用论文所使用的 Biased Spatial Reuse 配置，并从界面中移除了其他 spatial reuse 变体的切换开关。构建只生成该配置所需的 SPIR-V，适合直接用于论文截图和结果采集。

## 依赖

- Visual Studio 2026：使用“使用 C++ 的桌面开发”工作负载、C++20 工具链和 Windows 11 SDK。
- Vulkan SDK：支持根目录下的 `.deps/VulkanSDK` 本地 SDK，也支持通过 `VULKAN_SDK` 环境变量发现的系统安装。
- 其余依赖已包含在 `thirdparty` 中。
