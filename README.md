# Biased ReSTIR Direct Illumination in Vulkan

This repository contains a Windows Vulkan renderer implementing biased ReSTIR direct illumination. The paper configuration includes initial reservoir sampling, temporal reuse, biased spatial reuse, glTF material processing, Vulkan KHR hardware ray-traced visibility, and a compute-based AABB-tree visibility path.

## Included scene

Only the Sponza scene required to run and reproduce the paper configuration is included:

```text
scenes/Sponza/glTF/Sponza.gltf
```

Its source and licensing notes are preserved in `scenes/Sponza/README.md`.

## Build

Requirements:

- Windows 11
- Visual Studio 2026 with the C++ desktop workload
- CMake
- Vulkan SDK

Generate and build the Release configuration from a Visual Studio Developer PowerShell:

```powershell
cmake --preset vs2026-x64
cmake --build --preset vs2026-release
```

The executable is generated at:

```text
build/vs2026/bin/Release/ReSTIR.exe
```

See `BUILDING.md` for Visual Studio instructions and dependency details.

## Run Sponza

```powershell
build\vs2026\bin\Release\ReSTIR.exe --scene=scenes\Sponza\glTF\Sponza.gltf
```

When launched from the generated Visual Studio project, the Sponza argument is configured automatically.

## Third-party software

Third-party libraries required by the build are stored under `thirdparty/`. Their original copyright and licence notices are retained with their source files.
