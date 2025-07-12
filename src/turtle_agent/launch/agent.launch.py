from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    streaming_arg = DeclareLaunchArgument(
        'streaming',
        default_value='false',
        description='Enable streaming mode for the turtle agent'
    )
    
    turtle_agent_node = Node(
        package='turtle_agent',
        executable='turtle_agent.py',
        name='rosa_turtle_agent',
        output='screen',
        parameters=[{
            'streaming': LaunchConfiguration('streaming')
        }]
    )
    
    return LaunchDescription([
        streaming_arg,
        turtle_agent_node
    ])
