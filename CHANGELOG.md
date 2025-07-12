# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0]

### Added

* **Native Gemini SDK implementation** - Direct integration with Google's `google-generativeai` package for improved reliability
* **Complete ROS2 migration** - Full conversion from ROS1 to ROS2 with rclpy-based tools
* **Auto-detection of LLM providers** - Automatic selection between native Gemini and LangChain implementations
* **Function argument type conversion** - Automatic conversion of data types for ROS service compatibility
* **Comprehensive project documentation** - Added detailed documentation covering all features and changes
* **Debug utilities** - Added troubleshooting tools for development and testing

### Changed

* **Turtle tools completely rewritten** - Converted from rospy (ROS1) to rclpy (ROS2) for better performance
* **Launch files modernized** - Updated from ROS1 XML format to ROS2 Python format
* **Calculation functions restructured** - Modified for better Gemini API compatibility
* **Prompts enhanced** - Updated to be more action-oriented and ROS2-specific
* **Docker configuration improved** - Updated to ROS2 Humble base with proper dependencies
* **Import handling enhanced** - Better support for both direct execution and `ros2 run`

### Fixed

* **Gemini schema format errors** - Fixed `KeyError: 'object'` during tool conversion
* **Function calling response mismatch** - Resolved "400 function response parts" errors
* **ROS service type errors** - Fixed `'r' field must be of type 'int'` conversion issues
* **Import errors** - Fixed module import issues across different execution environments
* **Docker dependency issues** - Added missing `google-generativeai` package

### Removed

* **Unnecessary launch files** - Removed unused launch configurations
* **"Gen by Cursor" comments** - Cleaned up development artifacts from codebase

## [1.0.8]

### Changed

* Bumped LangChain versions

### Fixed

* Type hint errors in `ros2` tests

## [1.0.7]

### Added

* Support for local models using Ollama, particularly Llama >= 3.1

### Changed

* Bumped LangChain versions
* Updated ROS1 tools: `rosservice_call`, `roslaunch_list` and `rosnode_kill`

## [1.0.6]

### Added

* Implemented streaming capability for ROSA responses
* Added `pyproject.toml` for modern Python packaging
* Implemented asynchronous operations in TurtleAgent for better responsiveness

### Changed

* Updated Dockerfile for improved build process and development mode support
* Refactored TurtleAgent class for better modularity and streaming support
* Improved bounds checking for turtle movements
* Updated demo script for better cross-platform support and X11 forwarding
* Renamed `set_debuging` to `set_debugging` in system tools

### Fixed

* Corrected typos and improved documentation in various files
* Fixed potential issues with turtle movement calculations

### Removed

* Removed unnecessary logging statements from turtle tools

## [1.0.5]

### Added

* CI pipeline for automated testing
* Unit tests for ROSA tools and utilities

### Changed

* Improvements to various ROS2 tools
* Upgrade dependencies:
    * `langchain` to 0.2.14
    * `langchain_core` to 0.2.34
    * `langchain-openai` to 0.1.22

## [1.0.4]  - 2024-08-21

### Added

* Implemented ros2 topic echo tool.

### Changed

* Refactored ROS2 tools for better error handling and response parsing.
* Added blacklist parameters to relevant ROS2 tools.

### Fixed

* Fixed a bug where getting a list of ROS2 log files failed.

## [1.0.3]  - 2024-08-17

### Added

* `rosservice_call` tool for ROS1

### Changed

* Changed ROSA class methods from private to protected to allow easier overrides.
* Updated ros1 `roslog` tools to handle multiple logging directories.
* Upgrade dependencies:
    * `langchain` to 0.2.13
    * `langchain-community` to 0.2.12
    * `langchain_core` to 0.2.32
    * `langchain-openai` to 0.1.21

## [1.0.2] - 2024-08-14

### Changed

* Changed the `rostopic_echo` tool to both echo the topic and return the messages as a list

### Fixed

* Fixed a bug where both `ros1` and `ros2` tools were being imported before checking the `ros_version` parameter (#6) (
  ec578c10)

## [1.0.1] - 2024-08-10

### Added

* Added a working demo of ROSA controlling the TurtleSim robot in simulation

### Changed

* Changed the constructor of the `ROSA` class to accept tools in the form of `@tool` functions or Python packages
  containing `@tool` functions.
