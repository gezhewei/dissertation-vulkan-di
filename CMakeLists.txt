cmake_minimum_required(VERSION 3.24)

project(ReSTIR_DI LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

set(RESTIR_LOCAL_VULKAN_SDK "${CMAKE_CURRENT_SOURCE_DIR}/.deps/VulkanSDK")
if(EXISTS "${RESTIR_LOCAL_VULKAN_SDK}/Include/vulkan/vulkan.h")
    set(ENV{VULKAN_SDK} "${RESTIR_LOCAL_VULKAN_SDK}")
endif()

find_package(Vulkan REQUIRED)
find_program(
    RESTIR_GLSLC_EXECUTABLE
    NAMES glslc
    HINTS "$ENV{VULKAN_SDK}/Bin" "${RESTIR_LOCAL_VULKAN_SDK}/Bin"
    REQUIRED
)

# The source snapshot contains GLFW 3.2 headers and an x64 static library.
# Keeping this as an imported target avoids downloading dependencies during a VS build.
add_library(glfw STATIC IMPORTED GLOBAL)
set_target_properties(glfw PROPERTIES
    IMPORTED_LOCATION "${CMAKE_CURRENT_SOURCE_DIR}/thirdparty/imgui/examples/libs/glfw/lib-vc2010-64/glfw3.lib"
    INTERFACE_INCLUDE_DIRECTORIES "${CMAKE_CURRENT_SOURCE_DIR}/thirdparty/imgui/examples/libs/glfw/include"
    INTERFACE_LINK_LIBRARIES "user32;gdi32;shell32;winmm"
)

set(GFLAGS_BUILD_TESTING OFF CACHE BOOL "" FORCE)
set(GFLAGS_BUILD_PACKAGING OFF CACHE BOOL "" FORCE)
set(GFLAGS_BUILD_SHARED_LIBS OFF CACHE BOOL "" FORCE)
set(GFLAGS_INSTALL_HEADERS OFF CACHE BOOL "" FORCE)
set(GFLAGS_INSTALL_SHARED_LIBS OFF CACHE BOOL "" FORCE)
set(GFLAGS_INSTALL_STATIC_LIBS OFF CACHE BOOL "" FORCE)

add_subdirectory(thirdparty/MikkTSpace)
add_subdirectory(thirdparty/gltf)
target_link_libraries(gltf PUBLIC MikkTSpace)
add_subdirectory(thirdparty/gflags-src)
add_subdirectory(thirdparty/imgui)

set(RESTIR_SOURCES
    src/aabbTreeBuilder.cpp
    src/app.cpp
    src/glfwWindow.cpp
    src/main.cpp
    src/misc.cpp
    src/passes/gBufferPass.cpp
    src/swapchain.cpp
    src/vma.cpp
    src/vulkanDispatch.cpp
)

set(RESTIR_HEADERS
    src/aabbTreeBuilder.h
    src/app.h
    src/camera.h
    src/fpsCounter.h
    src/glfwWindow.h
    src/misc.h
    src/sceneBuffers.h
    src/shader.h
    src/shaderIncludes.h
    src/swapchain.h
    src/transientCommandBuffer.h
    src/vertex.h
    src/vma.h
    src/vulkanCompat.h
    src/passes/demoPass.h
    src/passes/gBufferPass.h
    src/passes/imguiPass.h
    src/passes/lightingPass.h
    src/passes/pass.h
    src/passes/restirPass.h
    src/passes/spatialReusePass.h
    src/passes/unbiasedReusePass.h
)

add_executable(ReSTIR ${RESTIR_SOURCES} ${RESTIR_HEADERS})
source_group(TREE "${CMAKE_CURRENT_SOURCE_DIR}/src" PREFIX "Source" FILES ${RESTIR_SOURCES} ${RESTIR_HEADERS})

target_include_directories(ReSTIR PRIVATE
    "${CMAKE_CURRENT_SOURCE_DIR}/src"
    "${CMAKE_CURRENT_SOURCE_DIR}/thirdparty/VulkanMemoryAllocator/include"
)

target_compile_definitions(ReSTIR PRIVATE
    NOMINMAX
    WIN32_LEAN_AND_MEAN
    VULKAN_HPP_DISPATCH_LOADER_DYNAMIC=1
)

if(MSVC)
    # The codebase uses vk::DispatchLoaderDynamic as exposed by older Vulkan-Hpp.
    # Force-include the small compatibility alias before every project translation unit.
    target_compile_options(ReSTIR PRIVATE /utf-8 /W3 /FIvulkanCompat.h)
endif()

target_link_libraries(ReSTIR PRIVATE
    Vulkan::Vulkan
    glfw
    imgui::imgui
    gltf
    MikkTSpace
    gflags::gflags
)

set(RESTIR_SHADER_STAGE_FILES
    src/shaders/gBuffer.frag
    src/shaders/gBuffer.vert
    src/shaders/hwVisibilityTest.rchit
    src/shaders/hwVisibilityTest.rmiss
    src/shaders/hwVisibilityTestShadow.rmiss
    src/shaders/lighting.frag
    src/shaders/quad.vert
    src/shaders/restirOmniHardware.rgen
    src/shaders/restirOmniSoftware.comp
    src/shaders/simple.frag
    src/shaders/simple.vert
    src/shaders/spatialReuse.comp
)

file(GLOB_RECURSE RESTIR_SHADER_INCLUDE_FILES CONFIGURE_DEPENDS
    "${CMAKE_CURRENT_SOURCE_DIR}/src/shaders/*.glsl"
)

set(RESTIR_SHADER_BUILD_DIR "${CMAKE_CURRENT_BINARY_DIR}/compiled_shaders")
set(RESTIR_SHADER_BINARIES)
foreach(SHADER_RELATIVE_PATH IN LISTS RESTIR_SHADER_STAGE_FILES)
    set(SHADER_SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/${SHADER_RELATIVE_PATH}")
    get_filename_component(SHADER_NAME "${SHADER_SOURCE}" NAME)
    set(SHADER_BINARY "${RESTIR_SHADER_BUILD_DIR}/${SHADER_NAME}.spv")
    add_custom_command(
        OUTPUT "${SHADER_BINARY}"
        COMMAND "${CMAKE_COMMAND}" -E make_directory "${RESTIR_SHADER_BUILD_DIR}"
        COMMAND "${RESTIR_GLSLC_EXECUTABLE}"
                --target-env=vulkan1.2
                -I "${CMAKE_CURRENT_SOURCE_DIR}/src/shaders"
                "${SHADER_SOURCE}"
                -o "${SHADER_BINARY}"
        DEPENDS "${SHADER_SOURCE}" ${RESTIR_SHADER_INCLUDE_FILES}
        VERBATIM
        COMMENT "Compiling ${SHADER_NAME}"
    )
    list(APPEND RESTIR_SHADER_BINARIES "${SHADER_BINARY}")
endforeach()

add_custom_target(restir_shaders ALL DEPENDS ${RESTIR_SHADER_BINARIES})
add_dependencies(ReSTIR restir_shaders)
source_group(TREE "${CMAKE_CURRENT_SOURCE_DIR}/src/shaders" PREFIX "Shaders" FILES
    ${RESTIR_SHADER_STAGE_FILES}
    ${RESTIR_SHADER_INCLUDE_FILES}
)
target_sources(ReSTIR PRIVATE ${RESTIR_SHADER_STAGE_FILES} ${RESTIR_SHADER_INCLUDE_FILES})
set_source_files_properties(${RESTIR_SHADER_STAGE_FILES} ${RESTIR_SHADER_INCLUDE_FILES}
    PROPERTIES HEADER_FILE_ONLY TRUE
)

add_custom_command(TARGET ReSTIR POST_BUILD
    COMMAND "${CMAKE_COMMAND}" -E make_directory "$<TARGET_FILE_DIR:ReSTIR>/shaders"
    COMMAND "${CMAKE_COMMAND}" -E copy_directory
            "${RESTIR_SHADER_BUILD_DIR}"
            "$<TARGET_FILE_DIR:ReSTIR>/shaders"
    VERBATIM
)

set_target_properties(ReSTIR PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/bin"
    VS_DEBUGGER_WORKING_DIRECTORY "$<TARGET_FILE_DIR:ReSTIR>"
    VS_DEBUGGER_COMMAND_ARGUMENTS "--scene=${CMAKE_CURRENT_SOURCE_DIR}/scenes/Sponza/glTF/Sponza.gltf"
)

if(EXISTS "${RESTIR_LOCAL_VULKAN_SDK}/Bin/VkLayer_khronos_validation.json")
    set_property(TARGET ReSTIR PROPERTY VS_DEBUGGER_ENVIRONMENT
        "VK_LAYER_PATH=${RESTIR_LOCAL_VULKAN_SDK}/Bin\nPATH=${RESTIR_LOCAL_VULKAN_SDK}/Bin;%PATH%"
    )
endif()

set_property(DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}" PROPERTY VS_STARTUP_PROJECT ReSTIR)
