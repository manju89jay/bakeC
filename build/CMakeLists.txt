cmake_minimum_required(VERSION 3.16)
project(bakec_generated C)

set(CMAKE_C_STANDARD 99)
set(CMAKE_C_STANDARD_REQUIRED ON)

if(NOT DEFINED PLATFORM)
    set(PLATFORM "desktop")
endif()

if(PLATFORM STREQUAL "desktop")
    set(GENERATED_DIR "${CMAKE_SOURCE_DIR}/../generated/desktop")
    add_compile_definitions(SIMULATION_MODE)
elseif(PLATFORM STREQUAL "cortex_m4")
    set(GENERATED_DIR "${CMAKE_SOURCE_DIR}/../generated/cortex_m4")
    include(cmake/toolchain_arm.cmake)
    add_compile_definitions(EMBEDDED_TARGET)
elseif(PLATFORM STREQUAL "aurix_tc397")
    set(GENERATED_DIR "${CMAKE_SOURCE_DIR}/../generated/aurix_tc397")
    include(cmake/toolchain_tricore.cmake)
    add_compile_definitions(EMBEDDED_TARGET AURIX_TC397 SIL2_SAFETY)
endif()

add_library(lung_controller STATIC
    ${GENERATED_DIR}/mnarx_lung_controller.c
    ${GENERATED_DIR}/mnarx_lung_controller_data.c
)
target_include_directories(lung_controller PUBLIC ${GENERATED_DIR})

add_library(pid_controller STATIC
    ${GENERATED_DIR}/pid_pressure_controller.c
    ${GENERATED_DIR}/pid_pressure_controller_data.c
)
target_include_directories(pid_controller PUBLIC ${GENERATED_DIR})

if(PLATFORM STREQUAL "desktop")
    enable_testing()

    add_executable(test_basis_functions
        ${CMAKE_SOURCE_DIR}/../tests/c/test_basis_functions.c
    )
    target_link_libraries(test_basis_functions lung_controller m)
    add_test(NAME basis_functions COMMAND test_basis_functions)

    add_executable(test_pid_controller
        ${CMAKE_SOURCE_DIR}/../tests/c/test_pid_controller.c
    )
    target_link_libraries(test_pid_controller pid_controller m)
    add_test(NAME pid_controller COMMAND test_pid_controller)
endif()
