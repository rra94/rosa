#!/usr/bin/env python3
"""
Test script to verify Gemini function calling works with ROSA
"""

import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool
from langchain_core.messages import ToolMessage

# Load environment variables
load_dotenv()

@tool(description="Get the current turtle pose")
def get_turtle_position() -> str:
    """Simple test tool that returns turtle position"""
    return "Turtle is at position (5.5, 5.5) facing 0 degrees"

def test_gemini_tools():
    """Test if Gemini can call tools properly"""
    
    # Initialize Gemini model
    llm = ChatGoogleGenerativeAI(
        model=os.getenv("GEMINI_MODEL", "gemini-1.5-flash"),
        temperature=0.0
    )
    
    # Bind tools
    llm_with_tools = llm.bind_tools([get_turtle_position])
    
    print("🧪 Testing Gemini Tool Calling...")
    print(f"Model: {llm.model}")
    
    # Test query
    query = "What is the current turtle position?"
    
    print(f"Query: {query}")
    
    try:
        # Invoke with tool calling
        response = llm_with_tools.invoke(query)
        
        print(f"Response type: {type(response)}")
        print(f"Response content: {response.content}")
        
        # Check for tool calls
        if hasattr(response, 'tool_calls') and response.tool_calls:
            print(f"✅ Tool calls found: {len(response.tool_calls)}")
            for i, tool_call in enumerate(response.tool_calls):
                print(f"  Tool {i+1}: {tool_call['name']}")
                print(f"  Args: {tool_call['args']}")
                
                # Execute the tool
                result = get_turtle_position.invoke(tool_call['args'])
                print(f"  Result: {result}")
                
                # Send result back to model
                tool_message = ToolMessage(
                    content=result,
                    tool_call_id=tool_call['id']
                )
                final_response = llm_with_tools.invoke([response, tool_message])
                print(f"  Final response: {final_response.content}")
            
            return True
        else:
            print("❌ No tool calls found in response")
            print("This suggests Gemini is not using function calling")
            return False
            
    except Exception as e:
        print(f"❌ Error during tool calling: {e}")
        return False

if __name__ == "__main__":
    success = test_gemini_tools()
    if success:
        print("\n🎉 Gemini tool calling works! The issue is elsewhere.")
    else:
        print("\n💥 Gemini tool calling failed. Check your configuration.") 