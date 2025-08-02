import requests
import json
from typing import List, Optional
from langchain_openai import AzureChatOpenAI


# System prompt template - moved out of class for clarity
SYSTEM_PROMPT_TEMPLATE = """You are a SAP Monitoring Assistant with access to system monitoring tools.

## Available Commands:
{command_help}

## Response Format:
When monitoring is needed, respond with ONLY this JSON structure:
{{"action": "monitoring", "server": "<server_name>", "command": "<command_name>", "params": {{}} }}

When monitoring is NOT needed, respond in plain English.

## Examples:
User: "Check CPU on server01" 
Response: {{"action": "monitoring", "server": "server01", "command": "cpu", "params": {{}} }}

User: "What commands are available?"
Response: I can help you monitor SAP servers with these commands: cpu, memory, get_process_list, and disk_usage."""


class SAPMonitoringAgent:
    """
    A clean, simple SAP monitoring agent without unnecessary LangChain complexity.
    """
    
    def __init__(self, api_key: str, azure_endpoint: str):
        self.MONITORING_DOMAIN = "mybank.net"
        
        self.COMMAND_SPECS = {
            "cpu": {"description": "Get current CPU usage", "params": {}},
            "memory": {"description": "Get current memory usage", "params": {}},
            "get_process_list": {
                "description": "Get list of running processes for a given instance",
                "params": {"instance": "00"}
            },
            "disk_usage": {
                "description": "Get disk usage stats for a mount point",
                "params": {"mount": "/hana"}
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
        
        # Build system prompt once
        command_help = "\n".join([
            f"- {cmd}: {spec['description']}, params: {spec['params']}"
            for cmd, spec in self.COMMAND_SPECS.items()
        ])
        self.system_prompt = SYSTEM_PROMPT_TEMPLATE.format(command_help=command_help)
    
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
        """Validate command and parameters."""
        if command not in self.COMMAND_SPECS:
            return False
        expected_keys = set(self.COMMAND_SPECS[command]["params"].keys())
        provided_keys = set(params.keys())
        return expected_keys.issubset(provided_keys)

    def _parse_json_response(self, response: str) -> Optional[dict]:
        """Parse JSON response - no LangChain parser needed!"""
        try:
            action = json.loads(response)
            if (action.get("action") == "monitoring" and 
                "server" in action and 
                "command" in action):
                return action
        except json.JSONDecodeError:
            pass
        return None

    def chat(self, chat_history: List[dict], max_steps: int = 3) -> str:
        """
        Main chat method - expects user input already in chat_history.
        
        Args:
            chat_history: Conversation messages including current user input
            max_steps: Maximum reasoning steps
            
        Returns:
            Assistant's response
        """
        # Build messages from chat history (includes system prompt and current user input)
        messages = list(chat_history)  # Copy chat history

        final_response = None
        
        for step in range(max_steps):
            # Get LLM response with error handling
            try:
                llm_response = self.llm.invoke(messages)
                content = llm_response.content.strip()
            except Exception as e:
                final_response = f"Error communicating with AI service: {str(e)}"
                break
            
            # Try to parse as tool call
            action = self._parse_json_response(content)
            
            if not action:
                # Plain text response - this is our final answer
                final_response = content
                break
                
            # We have a tool call - extract details (now safe due to validation)
            server = action["server"]
            command = action["command"]
            params = action.get("params", {}) or {}

            # Validate command
            if not self._validate_command(command, params):
                final_response = f"Invalid command or params: {command} {params}"
                break
                
            # Execute tool and add result to working messages
            result = self._call_agent_api(server, command, params)
                
            messages.append({"role": "assistant", "content": content})
            messages.append({"role": "system", "content": f"Tool result: {result}"})
            # Continue to next step for final response

        # If we hit max steps without a final response, return error
        if final_response is None:
            final_response = f"Unable to complete request within {max_steps} steps. Please try a simpler request."

        # Add only the final response to chat history (not tool call JSON)
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
