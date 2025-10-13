cmake_minimum_required(VERSION 3.16)

project(OdmTimeSync LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(PkgConfig REQUIRED)
pkg_check_modules(GPIOD REQUIRED IMPORTED_TARGET libgpiodcxx)
find_package(Threads REQUIRED)

add_executable(time_sync
	src/Odo_TimeSync.cpp
	src/TimeSync_Main.cpp
)

target_link_libraries(time_sync
	PRIVATE
		PkgConfig::GPIOD
		Threads::Threads
)

target_include_directories(time_sync
	PRIVATE
		${PROJECT_SOURCE_DIR}/src
)

target_compile_definitions(time_sync
	PRIVATE
		$<$<CONFIG:Debug>:TIME_SYNC_DEBUG>
)

target_compile_options(time_sync
	PRIVATE
		$<$<CXX_COMPILER_ID:GNU,Clang>:-Wall -Wextra -Wpedantic>
)
