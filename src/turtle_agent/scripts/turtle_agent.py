#!/usr/bin/env python3
"""
A simple turtle agent that uses ROSA to control a turtle in turtlesim.
"""

import os
import sys
import time
import threading
from typing import List, Optional

# Load environment variables from .env file first
try:
    import dotenv
    dotenv.load_dotenv(dotenv.find_dotenv())
except ImportError:
    print("Warning: python-dotenv not available, environment variables must be set manually")

# Add the scripts directory to the Python path for imports
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

import rclpy  # type: ignore
from rclpy.node import Node  # type: ignore

from rosa import ROSA
from rosa.gemini_rosa import GeminiROSA

# Handle both relative and absolute imports
try:
    from .llm import get_llm
    from .prompts import get_prompts
except ImportError:
    from llm import get_llm  # type: ignore
    from prompts import get_prompts  # type: ignore


class TurtleAgent(Node):
    """A simple turtle agent that uses ROSA to control a turtle in turtlesim."""
    
    def __init__(
        self,
        streaming: bool = True,
        verbose: bool = False,
        blacklist: Optional[List] = None,
        accumulate_chat_history: bool = True,
        show_token_usage: bool = False,
    ):
        super().__init__("turtle_agent")
        
        # Import turtle tools with flexible import handling
        try:
            from .tools import turtle
        except ImportError:
            from tools import turtle  # type: ignore
        
        # Get LLM provider
        llm_provider = os.getenv("LLM_PROVIDER", "gemini")
        
        # Initialize ROSA agent based on provider
        if llm_provider == "gemini":
            # Use native Gemini implementation
            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                print("Available environment variables:")
                for key, value in os.environ.items():
                    if 'API' in key or 'LLM' in key or 'GEMINI' in key:
                        print(f"  {key}={value[:10]}..." if len(value) > 10 else f"  {key}={value}")
                raise ValueError("GOOGLE_API_KEY environment variable is required for Gemini. Please check your .env file.")
            
            model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
            
            self.rosa = GeminiROSA(
                ros_version=2,
                api_key=api_key,
                model_name=model_name,
                tool_packages=[turtle],
                prompts=get_prompts(),
                verbose=verbose,
                blacklist=blacklist,
                accumulate_chat_history=accumulate_chat_history,
            )
            self.is_gemini = True
        else:
            # Use LangChain-based implementation
            llm = get_llm(streaming=streaming)
            self.rosa = ROSA(
                ros_version=2,
                llm=llm,
                tool_packages=[turtle],
                prompts=get_prompts(),
                verbose=verbose,
                blacklist=blacklist,
                accumulate_chat_history=accumulate_chat_history,
                show_token_usage=show_token_usage,
                streaming=streaming,
            )
            self.is_gemini = False
        
        self.streaming = streaming
        self.verbose = verbose
        
        # Store tools for direct access
        self.tools = [turtle]
        
        # Initialize ROS2 for turtle interaction
        self._init_ros()
        
        self.get_logger().info(f"TurtleAgent initialized with {llm_provider} provider")
    
    def _init_ros(self):
        """Initialize ROS2 components for turtle interaction."""
        # This will be handled by the turtle tools
        pass
    
    def process_query(self, query: str) -> str:
        """Process a user query and return the response."""
        if self.verbose:
            self.get_logger().info(f"Processing query: {query}")
        
        try:
            if self.is_gemini:
                # Native Gemini implementation - always use invoke
                return self.rosa.invoke(query)
            elif self.streaming and hasattr(self.rosa, 'astream'):
                # For streaming responses (LangChain implementation)
                response_parts = []
                
                async def collect_response():
                    async for chunk in self.rosa.astream(query):  # type: ignore
                        if chunk.get("type") == "token":
                            response_parts.append(chunk["content"])
                        elif chunk.get("type") == "final":
                            response_parts.append(chunk["content"])
                
                # Run async collection
                import asyncio
                asyncio.run(collect_response())
                
                return "".join(response_parts)
            else:
                # For non-streaming responses (both implementations)
                return self.rosa.invoke(query)
        except Exception as e:
            error_msg = f"Error processing query: {str(e)}"
            if self.verbose:
                self.get_logger().error(error_msg)
            return error_msg
    
    def clear_chat_history(self):
        """Clear the chat history."""
        self.rosa.clear_chat()
        
    def get_chat_history(self):
        """Get the chat history."""
        return self.rosa.chat_history


def main():
    """Main function for the turtle agent."""
    # Show current environment status
    print("🔧 Environment Status:")
    print(f"   LLM_PROVIDER: {os.getenv('LLM_PROVIDER', 'Not set')}")
    print(f"   GOOGLE_API_KEY: {'Set' if os.getenv('GOOGLE_API_KEY') else 'Not set'}")
    print(f"   GEMINI_MODEL: {os.getenv('GEMINI_MODEL', 'Not set')}")
    print()
    
    rclpy.init()
    
    # Get configuration from environment
    streaming = os.getenv("STREAMING", "True").lower() == "true"
    verbose = os.getenv("VERBOSE", "False").lower() == "true"
    
    try:
        # Create turtle agent
        agent = TurtleAgent(
            streaming=streaming,
            verbose=verbose,
        )
        
        # Interactive loop
        print("🐢 Turtle Agent is ready! Type 'exit' to quit.")
        print("Example: 'Draw a 5-point star using the turtle'")
        print("=" * 50)
        
        while True:
            try:
                user_input = input("\n> ").strip()
                
                if user_input.lower() in ['exit', 'quit', 'bye']:
                    print("Goodbye! 🐢")
                    break
                
                if user_input.lower() == 'clear':
                    agent.clear_chat_history()
                    print("Chat history cleared.")
                    continue
                
                if not user_input:
                    continue
                
                # Process the query
                print("\n🤖 Processing...")
                response = agent.process_query(user_input)
                print(f"\n🐢 {response}")
                
            except KeyboardInterrupt:
                print("\n\nGoodbye! 🐢")
                break
            except Exception as e:
                print(f"Error: {e}")
                
    except Exception as e:
        print(f"Failed to initialize turtle agent: {e}")
    finally:
        rclpy.shutdown()


if __name__ == "__main__":
    main()
