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

from typing import Any, AsyncIterable, Dict, Literal, Optional, List
try:
    import google.generativeai as genai  # type: ignore
    from google.generativeai import protos  # type: ignore
except ImportError:
    genai = None
    protos = None

from .prompts import RobotSystemPrompts, system_prompts
from .tools import ROSATools


class GeminiROSA:
    """Native Gemini implementation of ROSA that uses Google Gemini SDK directly.
    
    This implementation replaces the LangChain-based architecture with native Gemini
    function calling to provide better tool usage and more reliable execution.
    """
    
    def __init__(
        self,
        ros_version: Literal[1, 2],
        api_key: str,
        model_name: str = "gemini-2.5-flash",
        tools: Optional[list] = None,
        tool_packages: Optional[list] = None,
        prompts: Optional[RobotSystemPrompts] = None,
        verbose: bool = False,
        blacklist: Optional[list] = None,
        accumulate_chat_history: bool = True,
        temperature: float = 0.0,
    ):
        try:
            if genai is None:
                raise ImportError("google-generativeai package is required. Install with: pip install google-generativeai")
            
            if verbose:
                print("[GEMINI] Starting GeminiROSA initialization...")
            
            # Configure Gemini API
            genai.configure(api_key=api_key)  # type: ignore
            
            # Store configuration
            self.__ros_version = ros_version
            self.__verbose = verbose
            self.__blacklist = blacklist if blacklist else []
            self.__accumulate_chat_history = accumulate_chat_history
            self.__temperature = temperature
            
            if verbose:
                print("[GEMINI] Initializing tools...")
            
            # Initialize tools
            self.__tools = self._get_tools(
                ros_version, packages=tool_packages, tools=tools, blacklist=self.__blacklist
            )
            
            if verbose:
                print(f"[GEMINI] Found {len(self.__tools.get_tools())} tools")
            
            # Build system prompts
            if verbose:
                print("[GEMINI] Building system prompts...")
            self.__system_prompts = self._build_system_prompts(prompts)
            
            # Convert tools to Gemini format
            if verbose:
                print("[GEMINI] Converting tools to Gemini format...")
            self.__gemini_tools = self._convert_tools_to_gemini()
            
            if verbose:
                print(f"[GEMINI] Converted {len(self.__gemini_tools)} tools to Gemini format")
            
            # Initialize Gemini model with tools
            if verbose:
                print(f"[GEMINI] Initializing Gemini model: {model_name}")
            
            self.__model = genai.GenerativeModel(  # type: ignore
                model_name=model_name,
                tools=self.__gemini_tools,
                system_instruction=self.__system_prompts
            )
            
            if verbose:
                print("[GEMINI] Starting chat session...")
            
            # Initialize chat history
            self.__chat_history = []
            self.__chat = self.__model.start_chat(history=[])  # type: ignore
            
            if verbose:
                print("[GEMINI] GeminiROSA initialization completed successfully!")
                
        except Exception as e:
            error_msg = f"GeminiROSA initialization failed: {str(e)}"
            if verbose:
                print(f"[GEMINI ERROR] {error_msg}")
                import traceback
                traceback.print_exc()
            raise Exception(error_msg)
    
    @property
    def chat_history(self):
        """Get the chat history."""
        return self.__chat_history
    
    def clear_chat(self):
        """Clear the chat history."""
        self.__chat_history = []
        if self.__model:
            self.__chat = self.__model.start_chat(history=[])  # type: ignore
    
    def invoke(self, query: str) -> str:
        """
        Invoke the agent with a user query and return the response.
        
        Args:
            query (str): The user's input query to be processed by the agent.
            
        Returns:
            str: The agent's response to the query.
        """
        try:
            if self.__verbose:
                print(f"[GEMINI] Processing query: {query}")
            
            # Send message to Gemini
            response = self.__chat.send_message(query)
            
            # Process function calls if present
            final_response = self._process_response(response)
            
            # Record chat history
            if self.__accumulate_chat_history:
                self.__chat_history.append({"role": "user", "content": query})
                self.__chat_history.append({"role": "assistant", "content": final_response})
            
            return final_response
            
        except Exception as e:
            error_msg = f"An error occurred: {str(e)}"
            if self.__verbose:
                print(f"[GEMINI ERROR] {error_msg}")
            return error_msg
    
    def _process_response(self, response) -> str:
        """Process a Gemini response, handling function calls."""
        if self.__verbose:
            print(f"[GEMINI] Processing response with {len(response.candidates)} candidates")
        
        # Get the main response content
        candidate = response.candidates[0]
        content_parts = candidate.content.parts
        
        # Collect function calls and text parts
        text_parts = []
        function_calls = []
        
        for part in content_parts:
            if hasattr(part, 'text') and part.text:
                text_parts.append(part.text)
            elif hasattr(part, 'function_call') and part.function_call:
                function_calls.append(part.function_call)
        
        # If there are function calls, execute them and get the final response
        if function_calls:
            if self.__verbose:
                print(f"[GEMINI] Found {len(function_calls)} function calls to execute")
            
            # Execute all function calls and collect responses
            function_responses = []
            for function_call in function_calls:
                function_result = self._execute_function_call(function_call)
                
                if protos is not None:
                    function_response_part = protos.Part(  # type: ignore
                        function_response=protos.FunctionResponse(  # type: ignore
                            name=function_call.name,
                            response={"content": function_result},
                        )
                    )
                    function_responses.append(function_response_part)
            
            # Send all function responses back to the model at once
            if function_responses and protos is not None:
                if self.__verbose:
                    print(f"[GEMINI] Sending {len(function_responses)} function responses back to model")
                
                try:
                    final_response = self.__chat.send_message(function_responses)  # type: ignore
                    
                    # Get the final text response after function execution
                    final_candidate = final_response.candidates[0]
                    final_parts = final_candidate.content.parts
                    
                    for final_part in final_parts:
                        if hasattr(final_part, 'text') and final_part.text:
                            text_parts.append(final_part.text)
                            
                except Exception as e:
                    error_msg = f"Error sending function responses: {str(e)}"
                    if self.__verbose:
                        print(f"[GEMINI ERROR] {error_msg}")
                    return error_msg
        
        return " ".join(text_parts) if text_parts else "No response generated."
    
    def _execute_function_call(self, function_call) -> str:
        """Execute a function call and return the result."""
        function_name = function_call.name
        function_args = dict(function_call.args)
        
        if self.__verbose:
            print(f"[GEMINI] Executing function: {function_name} with args: {function_args}")
        
        # Find and execute the function
        for tool in self.__tools.get_tools():
            if tool.name == function_name:
                try:
                    # Check if tool.func is callable
                    if not callable(tool.func):
                        return f"Function {function_name} is not callable."
                    
                    # Convert argument types to match function signature
                    converted_args = self._convert_function_args(tool.func, function_args)
                    
                    result = tool.func(**converted_args)
                    result_str = str(result)
                    if self.__verbose:
                        print(f"[GEMINI] Function {function_name} returned: {result_str[:100]}...")
                    return result_str
                except Exception as e:
                    error_msg = f"Error executing {function_name}: {str(e)}"
                    if self.__verbose:
                        print(f"[GEMINI ERROR] {error_msg}")
                    return error_msg
        
        return f"Function {function_name} not found."
    
    def _convert_function_args(self, func, args: dict) -> dict:
        """Convert function arguments to match the expected parameter types."""
        import inspect
        
        # Get function signature
        sig = inspect.signature(func)
        converted_args = {}
        
        for param_name, param_value in args.items():
            if param_name in sig.parameters:
                param_type = sig.parameters[param_name].annotation
                
                # Skip conversion if no type annotation
                if param_type is None or param_type == inspect.Parameter.empty:
                    converted_args[param_name] = param_value
                    continue
                
                # Convert based on expected type
                if param_type == int and isinstance(param_value, (float, int)):
                    converted_args[param_name] = int(param_value)
                elif param_type == float and isinstance(param_value, (int, float)):
                    converted_args[param_name] = float(param_value)
                elif param_type == str:
                    converted_args[param_name] = str(param_value)
                elif param_type == bool:
                    converted_args[param_name] = bool(param_value)
                else:
                    # For other types (like List), keep as is
                    converted_args[param_name] = param_value
            else:
                # Parameter not in signature, keep as is
                converted_args[param_name] = param_value
        
        return converted_args
    
    def _get_tools(
        self,
        ros_version: Literal[1, 2],
        packages: Optional[list],
        tools: Optional[list],
        blacklist: Optional[list],
    ) -> ROSATools:
        """Create a ROSA tools object with the specified ROS version, tools, packages, and blacklist."""
        rosa_tools = ROSATools(ros_version, blacklist=blacklist)
        if tools:
            rosa_tools.add_tools(tools)
        if packages:
            rosa_tools.add_packages(packages, blacklist=blacklist)
        return rosa_tools
    
    def _build_system_prompts(self, robot_prompts: Optional[RobotSystemPrompts] = None) -> str:
        """Build system prompts from the default and robot-specific prompts."""
        prompts = []
        
        # Add default system prompts
        for role, content in system_prompts:
            prompts.append(content)
        
        # Add robot-specific prompts
        if robot_prompts:
            prompts.append(str(robot_prompts))
        
        return "\n\n".join(prompts)
    
    def _convert_tools_to_gemini(self) -> List:
        """Convert LangChain tools to Gemini function format."""
        gemini_tools = []
        
        for tool in self.__tools.get_tools():
            gemini_function = self._convert_tool_to_gemini_function(tool)
            gemini_tools.append(gemini_function)
        
        return gemini_tools
    
    def _convert_tool_to_gemini_function(self, tool):
        """Convert a single LangChain tool to Gemini function format."""
        import inspect
        
        try:
            # Get function signature
            sig = inspect.signature(tool.func)
            
            # Build parameters schema for Gemini (not JSON Schema)
            parameters = {
                "type_": "OBJECT",  # Use type_ instead of type for Gemini
                "properties": {},
                "required": []
            }
            
            for param_name, param in sig.parameters.items():
                # Skip 'self' parameter
                if param_name == 'self':
                    continue
                    
                # Get type annotation
                param_type = param.annotation
                
                if self.__verbose:
                    print(f"[GEMINI] Processing parameter {param_name} with type {param_type}")
                
                # Convert Python types to Gemini schema types
                if param_type == str:
                    param_schema = {"type_": "STRING"}
                elif param_type == int:
                    param_schema = {"type_": "INTEGER"}
                elif param_type == float:
                    param_schema = {"type_": "NUMBER"}
                elif param_type == bool:
                    param_schema = {"type_": "BOOLEAN"}
                elif hasattr(param_type, '__origin__'):
                    # Handle generic types like List[float]
                    if param_type.__origin__ == list:
                        item_type = param_type.__args__[0] if param_type.__args__ else str
                        if item_type == float:
                            param_schema = {"type_": "ARRAY", "items": {"type_": "NUMBER"}}
                        elif item_type == int:
                            param_schema = {"type_": "ARRAY", "items": {"type_": "INTEGER"}}
                        elif item_type == str:
                            param_schema = {"type_": "ARRAY", "items": {"type_": "STRING"}}
                        else:
                            param_schema = {"type_": "ARRAY", "items": {"type_": "STRING"}}
                    else:
                        param_schema = {"type_": "STRING"}
                elif param_type == inspect.Parameter.empty:
                    # No type annotation, default to string
                    param_schema = {"type_": "STRING"}
                else:
                    # Unknown type, default to string
                    if self.__verbose:
                        print(f"[GEMINI] Unknown parameter type {param_type} for {param_name}, defaulting to string")
                    param_schema = {"type_": "STRING"}
                
                parameters["properties"][param_name] = param_schema
                
                # Add to required if no default value
                if param.default == inspect.Parameter.empty:
                    parameters["required"].append(param_name)
            
            # Create Gemini function declaration
            function_def = {
                "name": tool.name,
                "description": tool.description,
                "parameters": parameters
            }
            
            if self.__verbose:
                print(f"[GEMINI] Converted tool {tool.name} to Gemini format")
                
            return function_def
            
        except Exception as e:
            error_msg = f"Error converting tool {tool.name} to Gemini format: {str(e)}"
            if self.__verbose:
                print(f"[GEMINI ERROR] {error_msg}")
            raise Exception(error_msg) 