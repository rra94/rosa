# ROSA Project Documentation

## Overview
ROSA (Robot Operating System Agent) is a ROS-based robotics agent with LLM capabilities, featuring a TurtleSim demonstration. The project now supports both LangChain-based implementations and native Gemini SDK implementation for better function calling reliability.

## Project Structure

### Core Components
- `src/rosa/`: Main ROSA module
  - `rosa.py`: Core ROSA agent implementation (LangChain-based)
  - `gemini_rosa.py`: Native Gemini SDK implementation **[NEW]**
  - `prompts.py`: LLM prompts and templates
  - `tools/`: Tool modules for various functionalities
    - `calculation.py`: Mathematical operations
    - `log.py`: Logging utilities
    - `ros1.py`: ROS1 compatibility layer
    - `ros2.py`: ROS2 integration
    - `system.py`: System operations

### TurtleSim Demo
- `src/turtle_agent/`: ROS2 TurtleSim demonstration package
  - `scripts/turtle_agent.py`: Main turtle agent script (supports both implementations)
  - `CMakeLists.txt`: CMake build configuration
  - `package.xml`: ROS2 package manifest
  - `tools/turtle.py`: Turtle control functions (ROS2-native)
  - `llm.py`: LLM configuration and initialization
  - `prompts.py`: Agent-specific prompts

## LLM Provider Support

### Native Gemini Implementation (Recommended)
- **File**: `src/rosa/gemini_rosa.py`
- **Advantages**: 
  - Better function calling reliability
  - No LangChain dependency for Gemini
  - Simpler architecture
  - More consistent tool execution
- **Configuration**: 
  - Set `LLM_PROVIDER=gemini` in .env
  - Requires `GOOGLE_API_KEY`
  - Optional: `GEMINI_MODEL` (default: gemini-1.5-flash)

### LangChain-based Implementation
- **File**: `src/rosa/rosa.py`
- **Supports**: OpenAI, Azure OpenAI, Ollama, and other LangChain providers
- **Configuration**: Set `LLM_PROVIDER` to provider name (e.g., `azure_openai`, `openai`, `ollama`)

## Recent Changes
- Fixed Dockerfile to use explicit ROS2 Humble turtlesim package instead of dynamic detection
- Updated pyproject.toml to require Python 3.10+ (changed from 3.9+)
- Verified turtle_agent uses ROS2 (rclpy) and Python 3.10
- Converted launch file from ROS1 XML format to ROS2 Python format (agent.launch.py)
- Updated CMakeLists.txt to properly install Python launch files
- Added launch and launch_ros dependencies to package.xml
- Fixed Docker dependency installation: Added explicit pip install for all dependencies to resolve ModuleNotFoundError for pyinputplus
- Fixed Python path configuration: Added PYTHONPATH=/app/src:/app/src/turtle_agent/scripts to ensure rosa module and tools module are found at runtime
- **MAJOR**: Converted turtle tools from ROS1 to ROS2: Complete rewrite of src/turtle_agent/scripts/tools/turtle.py to use rclpy instead of rospy, including publishers, service clients, and node management
- Fixed ROS2 context initialization issues: Added proper rclpy.ok() checks to prevent "Context.init() must only be called once" errors
- **MAJOR**: Restructured calculation functions for Gemini compatibility: Changed from nested List types to separate x_values/y_values parameters to meet Gemini API schema requirements
- Updated prompts to be more action-oriented: Added explicit instructions for agents to use tools instead of providing explanations
- **MAJOR**: Updated prompts to be ROS2-specific: Added references to ROS2 Humble, nodes, topics, services, and message passing concepts
- **CRITICAL**: Implemented native Gemini SDK support: Created GeminiROSA class that uses google-generativeai directly instead of LangChain, solving function calling reliability issues
- Updated turtle_agent.py to automatically detect and use native Gemini implementation when LLM_PROVIDER=gemini
- **CLEANUP**: Removed all "Gen by Cursor" comments from codebase
- **FIXED**: Import error when running turtle_agent.py directly: Added try/except blocks to handle both relative and absolute imports for compatibility with ros2 run command
- **FIXED**: Missing google-generativeai dependency in Dockerfile: Added explicit installation to ensure native Gemini implementation works in Docker environment
- **FIXED**: ROS2 dependencies made optional: GeminiROSA can now work without rclpy for development/testing outside ROS2 environment
- **CRITICAL**: Fixed Gemini schema format error: Changed from JSON Schema format (type: "object") to Gemini format (type_: "OBJECT") to resolve KeyError: 'object' during tool conversion
- **CRITICAL**: Fixed Gemini function calling response mismatch: Changed to collect all function calls first, then send all responses in one message to resolve "400 number of function response parts" error
- **CRITICAL**: Fixed function argument type conversion: Added `_convert_function_args()` method to convert float values to integers when functions expect integers (e.g., set_pen RGB values), resolving "The 'r' field must be of type 'int'" ROS service errors

## Configuration

### Environment Variables
- `LLM_PROVIDER`: Determines which LLM implementation to use
  - `gemini`: Use native Gemini implementation (recommended)
  - `azure_openai`: Use Azure OpenAI via LangChain
  - `openai`: Use OpenAI via LangChain
  - `ollama`: Use Ollama via LangChain
- `GOOGLE_API_KEY`: Required for Gemini
- `GEMINI_MODEL`: Gemini model name (default: gemini-1.5-flash)
- `VERBOSE`: Enable verbose logging
- `STREAMING`: Enable streaming responses (LangChain only)

### Docker Configuration
- Base image: ROS2 Humble
- Python: 3.10+
- Dependencies: All required packages installed via pip
- Environment: Properly configured PYTHONPATH for module resolution

## Database Schema
Not applicable - this is a ROS-based robotics agent without persistent database storage.

## Migration Notes
- **From ROS1 to ROS2**: All turtle tools converted to use rclpy
- **From LangChain to Native Gemini**: Automatic detection based on LLM_PROVIDER
- **Calculation Functions**: Updated to use separate x_values/y_values parameters instead of xy_pairs

## Testing
- Unit tests available in `tests/` directory
- Test coverage includes calculation functions, ROS tools, and core functionality
- All tests updated to use new calculation function signatures

## Key Features
- **Multi-LLM Support**: Native Gemini and LangChain-based providers
- **ROS2 Integration**: Full ROS2 Humble compatibility
- **Tool-based Architecture**: Modular tool system for extensibility
- **Function Calling**: Reliable tool execution with both implementations
- **TurtleSim Demo**: Interactive turtle control demonstration
- **Docker Support**: Containerized deployment with ROS2 environment 