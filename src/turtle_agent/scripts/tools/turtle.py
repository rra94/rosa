#  Copyright (c) 2024. Jet Propulsion Laboratory. All rights reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#  https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

from math import cos, sin, sqrt
from typing import List
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile
from geometry_msgs.msg import Twist
from langchain.agents import tool
from std_srvs.srv import Empty
from turtlesim.msg import Pose
from turtlesim.srv import Spawn, TeleportAbsolute, TeleportRelative, Kill, SetPen

# Global node instance for ROS2 operations
_turtle_node = None
cmd_vel_pubs = {}
pose_subscriptions = {}
latest_poses = {}


def get_turtle_node():
    """Get or create the turtle node for ROS2 operations."""
    global _turtle_node
    if _turtle_node is None:
        # Check if rclpy is already initialized
        if not rclpy.ok():
            rclpy.init(args=None)
        _turtle_node = Node('turtle_tools_node')
    return _turtle_node


def add_cmd_vel_pub(name: str):
    """Add a command velocity publisher for a turtle."""
    global cmd_vel_pubs
    node = get_turtle_node()
    qos_profile = QoSProfile(depth=10)
    cmd_vel_pubs[name] = node.create_publisher(Twist, f'/{name}/cmd_vel', qos_profile)


def remove_cmd_vel_pub(name: str):
    """Remove a command velocity publisher for a turtle."""
    global cmd_vel_pubs
    if name in cmd_vel_pubs:
        cmd_vel_pubs[name].destroy()
        cmd_vel_pubs.pop(name, None)


def add_pose_subscription(name: str):
    """Add a pose subscription for a turtle."""
    global pose_subscriptions, latest_poses
    node = get_turtle_node()
    
    def pose_callback(msg):
        latest_poses[name] = msg
    
    qos_profile = QoSProfile(depth=10)
    pose_subscriptions[name] = node.create_subscription(
        Pose, f'/{name}/pose', pose_callback, qos_profile
    )


def remove_pose_subscription(name: str):
    """Remove a pose subscription for a turtle."""
    global pose_subscriptions, latest_poses
    if name in pose_subscriptions:
        pose_subscriptions[name].destroy()
        pose_subscriptions.pop(name, None)
        latest_poses.pop(name, None)


# Turtle1 publisher and subscription will be initialized lazily when first used


def within_bounds(x: float, y: float) -> tuple:
    """
    Check if the given x, y coordinates are within the bounds of the turtlesim environment.

    :param x: The x-coordinate.
    :param y: The y-coordinate.
    """
    if 0 <= x <= 11 and 0 <= y <= 11:
        return True, "Coordinates are within bounds."
    else:
        return False, f"({x}, {y}) will be out of bounds. Range is [0, 11] for each."


def will_be_within_bounds(
    name: str, velocity: float, lateral: float, angle: float, duration: float = 1.0
) -> tuple:
    """Check if the turtle will be within bounds after publishing a twist command."""
    # Get the current pose of the turtle
    pose_dict = get_turtle_pose.invoke({"names": [name]})
    if "Error" in pose_dict:
        return False, pose_dict["Error"]
    
    current_pose = pose_dict[name]
    current_x = current_pose.x
    current_y = current_pose.y
    current_theta = current_pose.theta

    # Calculate the new position and orientation
    if abs(angle) < 1e-6:  # Straight line motion
        new_x = (
            current_x
            + (velocity * cos(current_theta) - lateral * sin(current_theta)) * duration
        )
        new_y = (
            current_y
            + (velocity * sin(current_theta) + lateral * cos(current_theta)) * duration
        )
    else:  # Circular motion
        radius = sqrt(velocity**2 + lateral**2) / abs(angle)
        center_x = current_x - radius * sin(current_theta)
        center_y = current_y + radius * cos(current_theta)
        angle_traveled = angle * duration
        new_x = center_x + radius * sin(current_theta + angle_traveled)
        new_y = center_y - radius * cos(current_theta + angle_traveled)

        # Check if any point on the circle is out of bounds
        for t in range(int(duration) + 1):
            angle_t = current_theta + angle * t
            x_t = center_x + radius * sin(angle_t)
            y_t = center_y - radius * cos(angle_t)
            in_bounds, _ = within_bounds(x_t, y_t)
            if not in_bounds:
                return (
                    False,
                    f"The circular path will go out of bounds at ({x_t:.2f}, {y_t:.2f}).",
                )

    # Check if the final x, y coordinates are within bounds
    in_bounds, message = within_bounds(new_x, new_y)
    if not in_bounds:
        return (
            False,
            f"This command will move the turtle out of bounds to ({new_x:.2f}, {new_y:.2f}).",
        )

    return True, f"The turtle will remain within bounds at ({new_x:.2f}, {new_y:.2f})."


@tool
def spawn_turtle(name: str, x: float, y: float, theta: float) -> str:
    """
    Spawn a turtle at the given x, y, and theta coordinates.

    :param name: name of the turtle.
    :param x: x-coordinate.
    :param y: y-coordinate.
    :param theta: angle.
    """
    in_bounds, message = within_bounds(x, y)
    if not in_bounds:
        return message

    # Remove any forward slashes from the name
    name = name.replace("/", "")

    node = get_turtle_node()
    client = node.create_client(Spawn, '/spawn')
    
    if not client.wait_for_service(timeout_sec=5.0):
        return f"Failed to spawn {name}: service not available."

    try:
        request = Spawn.Request()
        request.x = x
        request.y = y
        request.theta = theta
        request.name = name
        
        future = client.call_async(request)
        rclpy.spin_until_future_complete(node, future)
        
        if future.result() is not None:
            add_cmd_vel_pub(name)
            add_pose_subscription(name)
            return f"{name} spawned at x: {x}, y: {y}, theta: {theta}."
        else:
            return f"Failed to spawn {name}: service call failed."
    except Exception as e:
        return f"Failed to spawn {name}: {e}"


@tool
def kill_turtle(names: List[str]):
    """
    Removes a turtle from the turtlesim environment.

    :param names: List of names of the turtles to remove (do not include the forward slash).
    """
    # Remove any forward slashes from the names
    names = [name.replace("/", "") for name in names]
    response = ""
    node = get_turtle_node()

    for name in names:
        client = node.create_client(Kill, '/kill')
        
        if not client.wait_for_service(timeout_sec=5.0):
            response += f"Failed to kill {name}: /kill service not available.\n"
            continue
            
        try:
            request = Kill.Request()
            request.name = name
            
            future = client.call_async(request)
            rclpy.spin_until_future_complete(node, future)
            
            if future.result() is not None:
                remove_cmd_vel_pub(name)
                remove_pose_subscription(name)
                response += f"Successfully killed {name}.\n"
            else:
                response += f"Failed to kill {name}: service call failed.\n"
        except Exception as e:
            response += f"Failed to kill {name}: {e}\n"

    return response


@tool
def clear_turtlesim():
    """Clears the turtlesim background and sets the color to the value of the background parameters."""
    node = get_turtle_node()
    client = node.create_client(Empty, '/clear')
    
    if not client.wait_for_service(timeout_sec=5.0):
        return "Failed to clear the turtlesim background: /clear service not available."
        
    try:
        request = Empty.Request()
        future = client.call_async(request)
        rclpy.spin_until_future_complete(node, future)
        
        if future.result() is not None:
            return "Successfully cleared the turtlesim background."
        else:
            return "Failed to clear the turtlesim background: service call failed."
    except Exception as e:
        return f"Failed to clear the turtlesim background: {e}"


@tool
def get_turtle_pose(names: List[str]) -> dict:
    """
    Get the pose of one or more turtles.

    :param names: List of names of the turtles to get the pose of.
    """
    # Remove any forward slashes from the names
    names = [name.replace("/", "") for name in names]
    poses = {}
    node = get_turtle_node()

    # Get the pose of each turtle
    for name in names:
        if name not in pose_subscriptions:
            add_pose_subscription(name)
        
        # Spin for a short time to get the latest pose
        start_time = time.time()
        while name not in latest_poses and (time.time() - start_time) < 2.0:
            rclpy.spin_once(node, timeout_sec=0.1)
        
        if name in latest_poses:
            poses[name] = latest_poses[name]
        else:
            return {"Error": f"Failed to get pose for {name}: /{name}/pose not available."}
    
    return poses


@tool
def teleport_absolute(
    name: str, x: float, y: float, theta: float, hide_pen: bool = True
):
    """
    Teleport a turtle to the given x, y, and theta coordinates.

    :param name: name of the turtle
    :param x: The x-coordinate, range: [0, 11]
    :param y: The y-coordinate, range: [0, 11]
    :param theta: angle
    :param hide_pen: True to hide the pen (do not show movement trace on screen), False to show the pen
    """
    in_bounds, message = within_bounds(x, y)
    if not in_bounds:
        return message

    name = name.replace("/", "")
    node = get_turtle_node()
    client = node.create_client(TeleportAbsolute, f'/{name}/teleport_absolute')
    
    if not client.wait_for_service(timeout_sec=5.0):
        return f"Failed to teleport the {name}: /{name}/teleport_absolute service not available."

    try:
        if hide_pen:
            set_pen.invoke({"name": name, "r": 0, "g": 0, "b": 0, "width": 1, "off": 1})
        
        request = TeleportAbsolute.Request()
        request.x = x
        request.y = y
        request.theta = theta
        
        future = client.call_async(request)
        rclpy.spin_until_future_complete(node, future)
        
        if future.result() is not None:
            if hide_pen:
                set_pen.invoke({"name": name, "r": 30, "g": 30, "b": 255, "width": 1, "off": 0})
            
            current_pose = get_turtle_pose.invoke({"names": [name]})
            if "Error" not in current_pose:
                pose = current_pose[name]
                return f"{name} new pose: ({pose.x}, {pose.y}) at {pose.theta} radians."
            else:
                return f"{name} teleported to ({x}, {y}) at {theta} radians."
        else:
            return f"Failed to teleport the turtle: service call failed."
    except Exception as e:
        return f"Failed to teleport the turtle: {e}"


@tool
def teleport_relative(name: str, linear: float, angular: float):
    """
    Teleport a turtle relative to its current position.

    :param name: name of the turtle
    :param linear: linear distance
    :param angular: angular distance
    """
    in_bounds, message = will_be_within_bounds(name, linear, 0.0, angular)
    if not in_bounds:
        return message

    name = name.replace("/", "")
    node = get_turtle_node()
    client = node.create_client(TeleportRelative, f'/{name}/teleport_relative')
    
    if not client.wait_for_service(timeout_sec=5.0):
        return f"Failed to teleport the {name}: /{name}/teleport_relative service not available."
        
    try:
        request = TeleportRelative.Request()
        request.linear = linear
        request.angular = angular
        
        future = client.call_async(request)
        rclpy.spin_until_future_complete(node, future)
        
        if future.result() is not None:
            current_pose = get_turtle_pose.invoke({"names": [name]})
            if "Error" not in current_pose:
                pose = current_pose[name]
                return f"{name} new pose: ({pose.x}, {pose.y}) at {pose.theta} radians."
            else:
                return f"{name} teleported by linear: {linear}, angular: {angular}."
        else:
            return f"Failed to teleport the turtle: service call failed."
    except Exception as e:
        return f"Failed to teleport the turtle: {e}"


@tool
def publish_twist_to_cmd_vel(
    name: str,
    velocity: float,
    lateral: float,
    angle: float,
    steps: int = 1,
):
    """
    Publish a Twist message to the /{name}/cmd_vel topic to move a turtle robot.
    Use a combination of linear and angular velocities to move the turtle in the desired direction.

    :param name: name of the turtle (do not include the forward slash)
    :param velocity: linear velocity, where positive is forward and negative is backward
    :param lateral: lateral velocity, where positive is left and negative is right
    :param angle: angular velocity, where positive is counterclockwise and negative is clockwise
    :param steps: Number of times to publish the twist message
    """
    # Remove any forward slashes from the name
    name = name.replace("/", "")

    # Check if the movement will keep the turtle within bounds
    in_bounds, message = will_be_within_bounds(
        name, velocity, lateral, angle, duration=steps
    )
    if not in_bounds:
        return message

    vel = Twist()
    vel.linear.x, vel.linear.y, vel.linear.z = velocity, lateral, 0.0
    vel.angular.x, vel.angular.y, vel.angular.z = 0.0, 0.0, angle

    try:
        if name not in cmd_vel_pubs:
            add_cmd_vel_pub(name)
        
        pub = cmd_vel_pubs[name]
        node = get_turtle_node()

        for _ in range(steps):
            pub.publish(vel)
            time.sleep(1.0)  # ROS2 equivalent of rospy.sleep(1)
            rclpy.spin_once(node, timeout_sec=0.0)  # Process callbacks
            
    except Exception as e:
        return f"Failed to publish {vel} to /{name}/cmd_vel: {e}"
    finally:
        current_pose = get_turtle_pose.invoke({"names": [name]})
        if "Error" not in current_pose:
            pose = current_pose[name]
            return (
                f"New Pose ({name}): x={pose.x}, y={pose.y}, "
                f"theta={pose.theta} rads, "
                f"linear_velocity={pose.linear_velocity}, "
                f"angular_velocity={pose.angular_velocity}."
            )
        else:
            return f"Command sent to {name}, but couldn't retrieve final pose."


@tool
def stop_turtle(name: str):
    """
    Stop a turtle by publishing a Twist message with zero linear and angular velocities.

    :param name: name of the turtle
    """
    return publish_twist_to_cmd_vel.invoke(
        {
            "name": name,
            "velocity": 0.0,
            "lateral": 0.0,
            "angle": 0.0,
        }
    )


@tool
def reset_turtlesim():
    """
    Resets the turtlesim, removes all turtles, clears any markings, and creates a new default turtle at the center.
    """
    node = get_turtle_node()
    client = node.create_client(Empty, '/reset')
    
    if not client.wait_for_service(timeout_sec=5.0):
        return "Failed to reset the turtlesim environment: /reset service not available."
        
    try:
        request = Empty.Request()
        future = client.call_async(request)
        rclpy.spin_until_future_complete(node, future)
        
        if future.result() is not None:
            # Clear the cmd_vel publishers and pose subscriptions
            global cmd_vel_pubs, pose_subscriptions, latest_poses
            
            # Destroy existing publishers and subscriptions
            for pub in cmd_vel_pubs.values():
                pub.destroy()
            for sub in pose_subscriptions.values():
                sub.destroy()
                
            cmd_vel_pubs.clear()
            pose_subscriptions.clear()
            latest_poses.clear()
            
            # Re-add turtle1
            add_cmd_vel_pub("turtle1")
            add_pose_subscription("turtle1")

            return "Successfully reset the turtlesim environment. Ignore all previous commands, failures, and goals."
        else:
            return "Failed to reset the turtlesim environment: service call failed."
    except Exception as e:
        return f"Failed to reset the turtlesim environment: {e}"


@tool
def set_pen(name: str, r: int, g: int, b: int, width: int, off: int):
    """
    Set the pen color and width for the turtle. The pen is used to draw lines on the turtlesim canvas.

    :param name: name of the turtle
    :param r: red value
    :param g: green value
    :param b: blue value
    :param width: width of the pen.
    :param off: 0=on, 1=off
    """
    # Remove any forward slashes from the name
    name = name.replace("/", "")

    node = get_turtle_node()
    client = node.create_client(SetPen, f'/{name}/set_pen')
    
    if not client.wait_for_service(timeout_sec=5.0):
        return f"Failed to set the pen color for the turtle: /{name}/set_pen service not available."
        
    try:
        request = SetPen.Request()
        request.r = r
        request.g = g
        request.b = b
        request.width = width
        request.off = off
        
        future = client.call_async(request)
        rclpy.spin_until_future_complete(node, future)
        
        if future.result() is not None:
            return f"Successfully set the pen color for the turtle: {name}."
        else:
            return f"Failed to set the pen color for the turtle: service call failed."
    except Exception as e:
        return f"Failed to set the pen color for the turtle: {e}"


@tool
def has_moved_to_expected_coordinates(
    name: str, expected_x: float, expected_y: float, tolerance: float = 0.1
) -> str:
    """
    Check if the turtle has moved to the expected position.

    :param name: name of the turtle
    :param expected_x: expected x-coordinate
    :param expected_y: expected y-coordinate
    :param tolerance: tolerance level for the comparison
    """
    current_pose = get_turtle_pose.invoke({"names": [name]})
    if "Error" in current_pose:
        return current_pose["Error"]
    
    pose = current_pose[name]
    current_x = pose.x
    current_y = pose.y

    distance = ((current_x - expected_x) ** 2 + (current_y - expected_y) ** 2) ** 0.5
    if distance <= tolerance:
        return (
            f"{name} has moved to the expected position ({expected_x}, {expected_y})."
        )
    else:
        return f"{name} has NOT moved to the expected position ({expected_x}, {expected_y})."
