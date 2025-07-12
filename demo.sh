#!/usr/bin/env bash
# Copyright (c) 2024. Jet Propulsion Laboratory. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# This script launches the ROSA demo in Docker

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed. Please install Docker and try again."
    exit 1
fi

# Set default headless mode
HEADLESS=${HEADLESS:-false}
DEVELOPMENT=${DEVELOPMENT:-false}

# Enable X11 forwarding based on OS
case "$(uname)" in
    Linux*)
        echo "Enabling X11 forwarding for Linux..."
        # If running under WSL, use :0 for DISPLAY
        if grep -q "WSL" /proc/version; then
            export DISPLAY=:0
        else
            export DISPLAY=host.docker.internal:0
        fi
        xhost +
        ;;
    Darwin*)
        echo "Enabling X11 forwarding for macOS..."
        
        # Check if XQuartz is available
        if ! command -v xquartz &> /dev/null && ! ls /Applications/Utilities/XQuartz.app &> /dev/null 2>&1; then
            echo "Error: XQuartz is not installed. Please install XQuartz:"
            echo "  brew install --cask xquartz"
            echo "After installation, log out and log back in, then run this script again."
            exit 1
        fi
        
        # Start XQuartz if not running
        if ! pgrep -x "XQuartz" > /dev/null && ! pgrep -x "Xquartz" > /dev/null; then
            echo "Starting XQuartz..."
            open -a XQuartz
            sleep 3
        fi
        
        # Configure XQuartz for network connections
        defaults write org.xquartz.X11 nolisten_tcp -bool false 2>/dev/null || true
        
        # Set up X11 forwarding
        HOST_IP=$(ifconfig en0 | grep inet | grep -v inet6 | awk '{print $2}' 2>/dev/null)
        if [ -z "$HOST_IP" ]; then
            HOST_IP=$(ifconfig en1 | grep inet | grep -v inet6 | awk '{print $2}' 2>/dev/null)
        fi
        
        if [ -z "$HOST_IP" ]; then
            export DISPLAY=localhost:0
        else
            export DISPLAY=$HOST_IP:0
        fi
        
        echo "Using DISPLAY=$DISPLAY"
        
        if command -v xhost &> /dev/null; then
            xhost +localhost 2>/dev/null || true
            xhost +$HOST_IP 2>/dev/null || true
        fi
        ;;
    MINGW*|CYGWIN*|MSYS*)
        echo "Enabling X11 forwarding for Windows..."
        export DISPLAY=host.docker.internal:0
        ;;
    *)
        echo "Error: Unsupported operating system."
        exit 1
        ;;
esac

# Check if X11 forwarding is working (skip for macOS as it can be flaky)
if [[ "$(uname)" != "Darwin" ]]; then
    if ! xset q &>/dev/null; then
        echo "Error: X11 forwarding is not working. Please check your X11 server and try again."
        exit 1
    fi
fi

# Build and run the Docker container
CONTAINER_NAME="rosa-turtlesim-demo"
echo "Building the $CONTAINER_NAME Docker image..."

# Set platform for Apple Silicon Macs
BUILD_ARGS="--build-arg DEVELOPMENT=$DEVELOPMENT"
if [[ "$(uname)" == "Darwin" && "$(uname -m)" == "arm64" ]]; then
    echo "Detected Apple Silicon Mac - building for linux/amd64 platform"
    BUILD_ARGS="$BUILD_ARGS --platform linux/amd64"
fi

docker build $BUILD_ARGS -t $CONTAINER_NAME -f Dockerfile . || { 
    echo "Error: Docker build failed"
    echo "This may be due to platform compatibility issues on Apple Silicon Macs"
    echo "You can try running in headless mode: HEADLESS=true ./demo.sh"
    exit 1
}

echo "Running the Docker container..."

# Set up Docker arguments based on OS
DOCKER_ARGS="-it --rm --name $CONTAINER_NAME -e DISPLAY=$DISPLAY -e HEADLESS=$HEADLESS -e DEVELOPMENT=$DEVELOPMENT -v \"$PWD/src\":/app/src -v \"$PWD/tests\":/app/tests"

# Add OpenGL environment variables for graphics support
DOCKER_ARGS="$DOCKER_ARGS -e LIBGL_ALWAYS_INDIRECT=1 -e LIBGL_ALWAYS_SOFTWARE=1 -e GALLIUM_DRIVER=llvmpipe -e MESA_GL_VERSION_OVERRIDE=3.3"

# Add OS-specific arguments
case "$(uname)" in
    Linux*)
        DOCKER_ARGS="$DOCKER_ARGS -v /tmp/.X11-unix:/tmp/.X11-unix --network host"
        ;;
    Darwin*)
        # macOS Docker Desktop doesn't support --network host or X11 socket mounting
        echo "Note: Running with macOS Docker configuration"
        # Add Apple Silicon platform support if needed
        if [[ "$(uname -m)" == "arm64" ]]; then
            DOCKER_ARGS="$DOCKER_ARGS --platform linux/amd64"
        fi
        ;;
    MINGW*|CYGWIN*|MSYS*)
        DOCKER_ARGS="$DOCKER_ARGS -v /tmp/.X11-unix:/tmp/.X11-unix --network host"
        ;;
esac

eval "docker run $DOCKER_ARGS $CONTAINER_NAME"

# Disable X11 forwarding
case "$(uname)" in
    Linux*)
        xhost -
        ;;
    Darwin*)
        if command -v xhost &> /dev/null; then
            xhost -localhost 2>/dev/null || true
        fi
        ;;
    MINGW*|CYGWIN*|MSYS*)
        # Windows cleanup if needed
        ;;
esac

exit 0
