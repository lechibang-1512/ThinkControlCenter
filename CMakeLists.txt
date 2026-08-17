cmake_minimum_required(VERSION 3.10)
project(ThinkArchitectureViewer VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Qt setup
set(CMAKE_AUTOMOC ON)
set(CMAKE_AUTORCC ON)
set(CMAKE_AUTOUIC ON)

find_package(Qt5 COMPONENTS Core Widgets REQUIRED)

add_executable(ThinkArchitectureViewer
    main.cpp
    MainWindow.cpp
    MainWindow.h
    HardwareDiscovery.cpp
    HardwareDiscovery.h
    SystemMonitor.cpp
    SystemMonitor.h
    WakeupManager.cpp
    WakeupManager.h
)

target_link_libraries(ThinkArchitectureViewer PRIVATE Qt5::Widgets)
