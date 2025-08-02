import requests
import json
from typing import List, Optional
from langchain_openai import AzureChatOpenAI


# System prompt template - using function calling (no command redundancy needed)
SYSTEM_PROMPT_TEMPLATE = """You are a SAP Monitoring Assistant with access to system monitoring tools.

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


class SAPMonitoringAgent:
    """
    A clean, simple SAP monitoring agent without unnecessary LangChain complexity.
    """
    
    def __init__(self, api_key: str, azure_endpoint: str):
        self.MONITORING_DOMAIN = "mybank.net"
        
        self.COMMAND_SPECS = {
            "cpu_info": {
                "description": "Get current CPU usage", 
                "params": {},
                "required": [],  # No additional params required beyond server
                "agent_command": "top -bn1 | grep 'Cpu(s)' | head -1",
                "backend": "shell"
            },
            "memory_info": {
                "description": "Get current memory usage", 
                "params": {},
                "required": [],  # No additional params required beyond server
                "agent_command": "free -h",
                "backend": "shell"
            },
            "get_process_list": {
                "description": "Get list of running processes for a given instance",
                "params": {"instance": "00", "filter": "SAP*", "limit": "50"},
                "required": ["instance"],  # instance required, filter/limit optional
                "agent_command": "execute soap call",
                "backend": "soap"
            },
            "disk_usage": {
                "description": "Get disk usage stats for a path",
                "params": {"path": "/hana", "threshold": "80"},
                "required": ["path"],  # path required, threshold optional
                "agent_command": "df -h {{.path}}",
                "backend": "shell"
            }
        }
        
        # Simple LLM initialization with retry logic
        self.llm = AzureChatOpenAI(
            api_key=api_key,
            api_version="2024-08-01",
            azure_endpoint=azure_endpoint,
            model="gpt-4",
            max_retries=3,  # Built-in retry
            timeout=30,     # Timeout handling
        )
        
        # Generate tools from COMMAND_SPECS - single source of truth (Option C)
        self.tools = self._build_command_specific_tools()
        
        # Build system prompt (no command_help needed - tools provide this info)
        self.system_prompt = SYSTEM_PROMPT_TEMPLATE
    
    def _call_agent_api(self, server: str, command: str, params: dict = None) -> dict:
        """Execute monitoring command - simple and clean."""
        if params is None:
            params = {}
        try:
            url = f"http://{server}.{self.MONITORING_DOMAIN}:8090/execute"
            payload = {"name": command, "params": params}
            response = requests.post(url, json=payload, timeout=5)
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    def _validate_command(self, command: str, params: dict) -> bool:
        """Validate command and parameters using improved required field."""
        if command not in self.COMMAND_SPECS:
            return False
        
        spec = self.COMMAND_SPECS[command]
        required_keys = set(spec["required"])
        provided_keys = set(params.keys())
        
        # Check that all required parameters are provided
        return required_keys.issubset(provided_keys)
        # Note: Optional parameters can be missing - that's perfectly fine!

    def _parse_json_response(self, response: str) -> Optional[dict]:
        """Parse JSON response - DEPRECATED: Now using OpenAI function calling"""
        # This method is kept for backward compatibility but not used
        try:
            action = json.loads(response)
            if (action.get("action") == "monitoring" and 
                "server" in action and 
                "command" in action):
                return action
        except json.JSONDecodeError:
            pass
        return None

    def _execute_tool_call(self, tool_call) -> dict:
        """Execute a function tool call - handles command-specific functions"""
        function_name = tool_call["name"]
        function_args = tool_call["args"]  # Already a dict, no need to json.loads()
        
        # Function name IS the command name (cpu, memory, disk_usage, etc.)
        command = function_name
        server = function_args.get("server")
        
        # Extract parameters (everything except 'server')
        params = {k: v for k, v in function_args.items() if k != "server"}
        
        # Validate command exists
        if command not in self.COMMAND_SPECS:
            return {"error": f"Unknown command: {command}"}
        
        # Validate parameters (this should rarely fail with proper OpenAI schema)
        if not self._validate_command(command, params):
            return {"error": f"Invalid params for {command}: {params}"}
        
        # Execute monitoring command
        return self._call_agent_api(server, command, params)

    def _build_command_specific_tools(self):
        """Build OpenAI tools from improved COMMAND_SPECS with required field"""
        tools = []
        
        for cmd, spec in self.COMMAND_SPECS.items():
            # Build parameter properties for ALL available parameters
            param_properties = {"server": {"type": "string", "description": "Server name to monitor"}}
            
            # Start with server as always required
            required_params = ["server"]
            
            # Add all parameters from params (both required and optional)
            for param_name, default_val in spec["params"].items():
                is_required = param_name in spec["required"]
                param_properties[param_name] = {
                    "type": "string",
                    "description": f"{'Required' if is_required else 'Optional'} parameter for {cmd} command (default: {default_val})"
                }
            
            # Add only the required parameters to the required array
            required_params.extend(spec["required"])
            
            # Create function with command name directly
            tools.append({
                "type": "function",
                "function": {
                    "name": cmd,
                    "description": f"{spec['description']} on specified server",
                    "parameters": {
                        "type": "object",
                        "properties": param_properties,
                        "required": required_params
                    }
                }
            })
        
        return tools

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
    agent = SAPMonitoringAgent(
        api_key="YOUR_KEY",
        azure_endpoint="https://your-endpoint.openai.azure.com/"
    )
    
    print("=== SAP Monitoring Assistant ===")
    print("Type your monitoring requests or 'quit' to exit")
    print("Examples: 'Check CPU on hana01', 'Get memory usage for server02'")
    print("-" * 50)
    
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
