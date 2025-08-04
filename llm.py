import json
from typing import List, Dict, Any
from langchain_openai import AzureChatOpenAI

from command_loader import CommandLoader
from command_builder import CommandBuilder
from agent import Agent
from function_schema_builder import FunctionSchemaBuilder


# Shared singletons - created once and reused
class SharedResources:
    """Simple container for shared resources - no fancy singleton pattern"""
    def __init__(self):
        self.commands_loader = None
        self.command_builder = None
        self.agent = None
        self.function_schema_builder = None
        self.tools = None
        self.system_prompt = None
        self.initialized = False
    
    def initialize(self, commands_file: str = "commands.yaml"):
        """Initialize all shared resources"""
        if self.initialized:
            return
            
        # Create shared objects once
        self.commands_loader = CommandLoader(commands_file)
        commands = self.commands_loader.get_commands()
        
        # Hard-coded monitoring domain (not part of function schemas)
        monitoring_domain = "mybank.net"
        
        self.command_builder = CommandBuilder(commands)
        self.agent = Agent(monitoring_domain)
        self.function_schema_builder = FunctionSchemaBuilder(commands)
        self.tools = self.function_schema_builder.build_function_schemas()
        
        # System prompt
        self.system_prompt = """You are a SAP Monitoring Assistant with access to system monitoring tools.

## Instructions:
- Use the available monitoring functions to check server status
- Provide explanations and analysis in natural language
- You can call multiple monitoring commands in sequence
- Always interpret and explain the monitoring results to the user

## Examples:
User: "Check CPU and disk usage on server01"
Response: I'll check both CPU and disk usage for server01.
[Function calls will be made automatically based on available tools]
Then provide analysis of both results."""
        
        self.initialized = True
        print(f"Shared resources initialized with {len(commands)} commands")


class SAPMonitoringAgent:
    """
    Lightweight SAP monitoring agent that uses explicitly passed shared resources.
    """
    
    def __init__(self, api_key: str, azure_endpoint: str, shared_resources: SharedResources):
        """
        Initialize agent with explicitly passed shared resources.
        
        Args:
            api_key: Azure OpenAI API key
            azure_endpoint: Azure OpenAI endpoint
            shared_resources: SharedResources instance with all shared objects
        """
        if not shared_resources.initialized:
            raise RuntimeError("SharedResources not initialized!")
            
        # Store reference to shared resources
        self.shared = shared_resources
        
        # Only create the LLM client per agent
        self.llm = AzureChatOpenAI(
            api_key=api_key,
            api_version="2024-08-01",
            azure_endpoint=azure_endpoint,
            model="gpt-4",
            max_retries=3,
            timeout=30,
        )
        
        # Direct access to shared resources
        self.tools = self.shared.tools
        self.system_prompt = self.shared.system_prompt
    
    def _execute_tool_call(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a function tool call - handles command-specific functions"""
        function_name = tool_call["name"]
        function_args = tool_call["args"]  # Already a dict, no need to json.loads()
        
        # Function name IS the command name (cpu_info, memory_info, disk_usage, etc.)
        command = function_name
        server = function_args.get("server")
        
        # Extract parameters (everything except 'server')
        params = {k: v for k, v in function_args.items() if k != "server"}
        
        # Validate command exists and parameters are valid using shared command builder
        if not self.shared.command_builder.validate_command(command, params):
            return {"error": f"Invalid command '{command}' or parameters: {params}"}
        
        # Get command specification from CommandLoader
        command_spec = self.shared.commands_loader.get_command_spec(command)
        if not command_spec:
            return {"error": f"Unknown command: {command}"}
        
        # Build the actual command using shared command builder
        actual_command = self.shared.command_builder.build_command(command_spec, params)
        
        # Execute monitoring command via shared agent with error handling
        try:
            return self.shared.agent.call_agent_api(
                server=server,
                command=actual_command,
                backend=command_spec["backend"],
                timeout=command_spec.get("timeout", 30)
            )
        except Exception as e:
            return {"error": f"Agent API call failed: {str(e)}"}

    def chat(self, chat_history: List[dict], max_steps: int = 3) -> str:
        """
        Main chat method using OpenAI function calling - much more robust!
        
        Args:
            chat_history: Conversation messages including current user input
            max_steps: Maximum reasoning steps
            
        Returns:
            Assistant's response
        """
        # Build messages from chat history
        messages = list(chat_history)  # Copy chat history

        final_response = None
        
        for step in range(max_steps):
            # Get LLM response with function calling capability
            try:
                llm_response = self.llm.invoke(
                    messages, 
                    tools=self.tools,
                    tool_choice="auto"  # Let LLM decide when to use tools
                )
                content = llm_response.content.strip() if llm_response.content else ""
                tool_calls = llm_response.tool_calls or []
                
            except Exception as e:
                final_response = f"Error communicating with AI service: {str(e)}"
                break
            
            # Add assistant message to working messages
            assistant_msg = {"role": "assistant", "content": content}
            if tool_calls:
                assistant_msg["tool_calls"] = [
                    {
                        "id": tc["id"],
                        "type": "function", 
                        "function": {"name": tc["name"], "arguments": tc["args"]}
                    } for tc in tool_calls
                ]
            messages.append(assistant_msg)
            
            # Process any tool calls
            if tool_calls:
                for tool_call in tool_calls:
                    # Execute the tool
                    result = self._execute_tool_call(tool_call)
                    
                    # Add tool result to working messages
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "content": json.dumps(result)
                    })
                
                # Continue to next step to get final response with tool results
                continue
            else:
                # No tool calls - this is our final response
                final_response = content
                break

        # If we hit max steps without a final response, return error
        if final_response is None:
            final_response = f"Unable to complete request within {max_steps} steps. Please try a simpler request."

        # Add only the final response to chat history (not tool call details)
        chat_history.append({"role": "assistant", "content": final_response})
        return final_response

# ------------------------
# Usage Examples
# ------------------------
def main():
    """Interactive SAP monitoring chat interface."""
    
    # Create shared resources ONCE - you can clearly see what's being created
    print("Creating shared resources...")
    shared_resources = SharedResources()
    
    # Initialize shared resources ONCE at startup
    try:
        shared_resources.initialize(commands_file="commands.yaml")
    except Exception as e:
        print(f"Failed to initialize shared resources: {e}")
        print("\nPlease ensure:")
        print("1. PyYAML is installed: pip install pyyaml")
        print("2. commands.yaml exists in the same directory")
        return
    
    # Now create lightweight agent - passing shared resources explicitly
    try:
        agent = SAPMonitoringAgent(
            api_key="YOUR_KEY",
            azure_endpoint="https://your-endpoint.openai.azure.com/",
            shared_resources=shared_resources  # Explicit dependency injection
        )
        
        print("=== SAP Monitoring Assistant ===")
        print(f"Loaded {len(shared_resources.commands_loader.get_commands())} commands from configuration")
        print("Type your monitoring requests or 'quit' to exit")
        print("Examples: 'Check CPU on hana01', 'Get memory usage for server02'")
        print("-" * 50)
        
    except Exception as e:
        print(f"Failed to initialize SAP Monitoring Agent: {e}")
        print("Please ensure your Azure OpenAI credentials are correct")
        return
    
    # Initialize chat history with system prompt (added once!)
    chat_history = [{"role": "system", "content": agent.system_prompt}]
    
    while True:
        try:
            user_input = input("\n> ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("Goodbye!")
                break
                
            if not user_input:
                continue
                
            # Add user input to chat history BEFORE calling chat
            chat_history.append({"role": "user", "content": user_input})
            
            # Keep chat history manageable (last 20 messages + system prompt)
            if len(chat_history) > 21:  # system + 20 messages
                chat_history = [chat_history[0]] + chat_history[-20:]  # Keep system + last 20
            
            # Get response - no need to pass user_input separately!
            response = agent.chat(chat_history)
            print(f"\nAssistant: {response}")
            
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}")
            print("Please try again.")


if __name__ == "__main__":
    main()
