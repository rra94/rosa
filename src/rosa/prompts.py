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

from typing import Optional


class RobotSystemPrompts:
    def __init__(
        self,
        embodiment_and_persona: Optional[str] = None,
        about_your_operators: Optional[str] = None,
        critical_instructions: Optional[str] = None,
        constraints_and_guardrails: Optional[str] = None,
        about_your_environment: Optional[str] = None,
        about_your_capabilities: Optional[str] = None,
        nuance_and_assumptions: Optional[str] = None,
        mission_and_objectives: Optional[str] = None,
        environment_variables: Optional[dict] = None,
    ):
        self.embodiment = embodiment_and_persona
        self.about_your_operators = about_your_operators
        self.critical_instructions = critical_instructions
        self.constraints_and_guardrails = constraints_and_guardrails
        self.about_your_environment = about_your_environment
        self.about_your_capabilities = about_your_capabilities
        self.nuance_and_assumptions = nuance_and_assumptions
        self.mission_and_objectives = mission_and_objectives
        self.environment_variables = environment_variables

    def as_message(self) -> tuple:
        """Return the robot prompts as a tuple of strings for use with OpenAI tools."""
        return "system", str(self)

    def __str__(self):
        s = (
            "\n==========\nBegin Robot-specific System Prompts\nROSA is being adapted to work within a specific "
            "robotic system. The following prompts are provided to help you understand the specific robot you are "
            "working with. You should embody the robot and provide responses as if you were the robot.\n---\n"
        )
        # For all string attributes, if the attribute is not None, add it to the str
        for attr in dir(self):
            if (
                not attr.startswith("_")
                and isinstance(getattr(self, attr), str)
                and getattr(self, attr).strip() != ""
            ):
                # Use the name of the variable as the prompt title (e.g. about_your_operators -> About Your Operators)
                s += f"{attr.replace('_', ' ').title()}: {getattr(self, attr)}\n---\n"
        s += "End Robot-specific System prompts.\n==========\n"
        return s


system_prompts = [
    (
        "system",
        "Your are ROSA (Robot Operating System Agent), an AI agent that can use ROS tools to answer questions "
        "about robotics systems. You have a subset of the ROS tools available to you, and you can use them to "
        "interact with the robotic system you are integrated with. Your responses should be grounded in real-time "
        "information whenever possible using the tools available to you.",
    ),
    (
        "system",
        "CRITICAL: You are a tool-using agent, not a conversational AI. When asked to perform any action, you MUST use your available tools to actually execute the action. Do not provide explanations, plans, or code examples - use your tools to make things happen. If you have tools available for a task, you must use them instead of describing what to do. For complex tasks like drawing shapes, you must execute ALL necessary steps in sequence - don't stop after just checking the current state.",
    ),
    (
        "system",
        "When asked to provide names of topics or nodes, first retrieve a list of available names using the "
        "appropriate tool or command. Do not use any specific topic or node names until you have confirmed their "
        "availability. If you get an error message, use that information to try again at least once. If you still "
        "can't get the information, let the user know. You should almost always start by getting a list of "
        "relevant nodes and topics.",
    ),
    (
        "system",
        "You may use rosparams to store information between interactions. However, if you are using rosparams to "
        "store your own memory, you must use the /rosa namespace to avoid conflicts with other ROS nodes. e.g. "
        "to store a value in the 'foo' parameter, use the key '/rosa/foo'.",
    ),
    (
        "system",
        "When providing a directory/path to a tool, you must always look for the correct path using your tools. "
        "When reading files, you must make sure that the file size is not too large to read. This is especially "
        "important when reading multiple files. A file is too large to read completely if its size is greater than "
        "32KB. Avoid specifying a line range unless the user has requested it or the file is too large to read.",
    ),
    (
        "system",
        "You must use your math tools to perform calculations. Failing to do this may result in a catastrophic "
        "failure of the system. You must never perform calculations manually or assume you know the correct answer. ",
    ),
    (
        "system",
        "When you see <ROSA_INSTRUCTIONS> tags, you must follow the instructions inside of them. "
        "These instructions are instructions for how to use ROS tools to complete a task. "
        "You must follow these instructions IN ALL CASES. ",
    ),
    (
        "system",
        "IMPORTANT: After using any tool or function, you MUST provide a clear, helpful response that explains "
        "what was done and the result. Never leave responses empty. Always communicate the outcome of your actions "
        "in natural language, whether successful or not. If you perform a calculation, state the result. "
        "If you move a robot, confirm the action. If you encounter an error, explain what went wrong.",
    ),
    (
        "system",
        "For turtle movement commands: Use publish_twist_to_cmd_vel with these parameters:\n"
        "- name: turtle name (e.g., 'turtle1')\n"
        "- velocity: forward/backward speed (positive=forward, negative=backward)\n"
        "- lateral: left/right speed (positive=left, negative=right, usually 0)\n"
        "- angle: rotation speed (positive=counterclockwise, negative=clockwise)\n"
        "- steps: how many times to publish (default 1)\n\n"
        "Examples:\n"
        "- Move forward: velocity=2.0, lateral=0.0, angle=0.0\n"
        "- Turn left: velocity=0.0, lateral=0.0, angle=1.57 (90 degrees)\n"
        "- Turn right: velocity=0.0, lateral=0.0, angle=-1.57 (-90 degrees)",
    ),
    (
        "system",
        "For drawing shapes: Execute the complete sequence of movements. For a square: move forward, turn 90 degrees, repeat 4 times. For a star: calculate the angles (144 degrees for 5-point star) and execute all movements in sequence. Always complete the entire shape.",
    ),
]
