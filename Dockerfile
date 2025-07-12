FROM osrf/ros:humble-desktop AS rosa-ros2
LABEL authors="Rob Royce"

ENV DEBIAN_FRONTEND=noninteractive
ENV HEADLESS=false
ARG DEVELOPMENT=false

# Install linux packages
RUN apt-get update && apt-get install -y \
    ros-humble-turtlesim \
    locales \
    xvfb \
    python3.10 \
    python3-pip \
    libgl1-mesa-glx \
    libgl1-mesa-dri \
    libglu1-mesa \
    mesa-utils \
    libxrender1 \
    libxext6 \
    libx11-6 \
    libxft2 \
    libxss1 \
    libgconf-2-4 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxi6 \
    libxtst6 \
    libxrandr2

# RUN apt-get clean && rm -rf /var/lib/apt/lists/*
RUN pip3 install -U python-dotenv

RUN rosdep update && \
    echo "source /opt/ros/humble/setup.bash" >> /root/.bashrc && \
    echo "export PYTHONPATH=/app/src:/app/src/turtle_agent/scripts:\$PYTHONPATH" >> /root/.bashrc && \
    echo "alias start='cd /app && export PYTHONPATH=/app/src:/app/src/turtle_agent/scripts:\$PYTHONPATH && colcon build && source install/setup.bash && ros2 run turtle_agent turtle_agent.py'" >> /root/.bashrc && \
    echo "export ROS_DOMAIN_ID=0" >> /root/.bashrc

COPY . /app/
WORKDIR /app/

# Set environment variables for graphics/OpenGL
ENV LIBGL_ALWAYS_INDIRECT=1
ENV LIBGL_ALWAYS_SOFTWARE=1
ENV GALLIUM_DRIVER=llvmpipe
ENV MESA_GL_VERSION_OVERRIDE=3.3

# Set Python path to include src directory and scripts directory
ENV PYTHONPATH=/app/src:/app/src/turtle_agent/scripts:$PYTHONPATH

# Upgrade setuptools to support PEP 660 editable installs
RUN pip3 install --upgrade setuptools>=64.0.0

# Install dependencies first to ensure proper resolution
RUN pip3 install \
    PyYAML==6.0.1 \
    python-dotenv>=1.0.1 \
    langchain~=0.3.23 \
    langchain-community~=0.3.21 \
    langchain-core~=0.3.52 \
    langchain-openai~=0.3.14 \
    langchain-ollama~=0.3.2 \
    langchain-google-genai~=2.0.8 \
    google-generativeai>=0.8.0 \
    pydantic \
    pyinputplus \
    azure-identity \
    cffi \
    rich \
    pillow>=10.4.0 \
    numpy>=1.26.4

# Install the local package with all dependencies
RUN /bin/bash -c 'cd /app && pip3 install -e .'

CMD ["/bin/bash", "-c", "source /opt/ros/humble/setup.bash && \
    export PYTHONPATH=/app/src:/app/src/turtle_agent/scripts:$PYTHONPATH && \
    ros2 daemon start > /dev/null 2>&1 & \
    sleep 5 && \
    if [ \"$HEADLESS\" = \"false\" ]; then \
    ros2 run turtlesim turtlesim_node & \
    else \
    xvfb-run -a -s \"-screen 0 1920x1080x24\" ros2 run turtlesim turtlesim_node & \
    fi && \
    sleep 5 && \
    echo \"Run \\`start\\` to build and launch the ROSA-TurtleSim demo.\" && \
    /bin/bash"]
