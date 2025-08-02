import requests
import json
from openai import AzureOpenAI
from typing import Dict, List, Optional


class SAPMonitoringAgent:
    """
    An AI agent that helps monitor SAP servers through conversational interface.
    Uses Azure OpenAI to understand natural language requests and execute monitoring commands.
    """
    
    def __init__(self, api_key: str, azure_endpoint: str):
        # Configuration
        self.MONITORING_DOMAIN = "mybank.net"
        self.MODEL = "gpt-4"
        
        # Available monitoring commands
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
        
        # Initialize Azure OpenAI client
        self.client = AzureOpenAI(
            api_key=api_key,
            api_version="2024-08-01",
            azure_endpoint=azure_endpoint,
        )
        
        # Build system prompt
        self.system_message = self._build_system_message()

    
    def _build_system_message(self) -> str:
        """Build the system message with available commands."""
        command_help = "\n".join([
            f"- {cmd}: {spec['description']}, params: {spec['params']}"
            for cmd, spec in self.COMMAND_SPECS.items()
        ])
        
        return f"""You are a SAP Monitoring Assistant.

You can call the tool: monitoring(server: str, command: str, params: dict)

Available commands:
{command_help}

Instructions:
1. If monitoring tool is needed, output ONLY JSON in this format:
   {{
     "action": "monitoring",
     "server": "<server>",
     "command": "<command>",
     "params": {{}}
   }}
2. Populate params exactly as defined in the command list.
3. If no monitoring call is needed, respond in plain English."""

    def _call_monitoring_api(self, server: str, command: str, params: Dict = None) -> Dict:
        """Execute monitoring command on SAP server."""
        if params is None:
            params = {}
        try:
            url = f"http://{server}.{self.MONITORING_DOMAIN}:8090/execute"
            payload = {"name": command, "params": params}
            response = requests.post(url, json=payload, timeout=5)
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    def _validate_command(self, command: str, params: Dict) -> bool:
        """Validate if command and parameters are correct."""
        if command not in self.COMMAND_SPECS:
            return False
        expected_keys = set(self.COMMAND_SPECS[command]["params"].keys())
        provided_keys = set(params.keys())
        return expected_keys.issubset(provided_keys)

    def _call_llm(self, messages: List[Dict]) -> str:
        """Send messages to Azure OpenAI and get response."""
        response = self.client.chat.completions.create(
            model=self.MODEL,
            messages=messages,
            temperature=0
        )
        return response.choices[0].message.content.strip()

    def _parse_llm_response(self, response: str) -> Optional[Dict]:
        """Try to parse LLM response as JSON tool call."""
        try:
            action = json.loads(response)
            if action.get("action") == "monitoring":
                return action
        except json.JSONDecodeError:
            pass
        return None

    def _execute_tool_call(self, action: Dict) -> Dict:
        """Execute a monitoring tool call."""
        server = action["server"]
        command = action["command"] 
        params = action.get("params", {}) or {}
        
        # Validate command
        if not self._validate_command(command, params):
            return {"error": f"Invalid command or params: {command} {params}"}
        
        # Execute monitoring call
        return self._call_monitoring_api(server, command, params)

    def chat(self, user_input: str, chat_history: List[Dict], max_steps: int = 3) -> str:
        """
        Main conversation method. Handles user input and returns assistant response.
        
        Args:
            user_input: User's question/request
            chat_history: List of {"role": "user"/"assistant", "content": str}
            max_steps: Maximum reasoning steps to prevent infinite loops
            
        Returns:
            Assistant's response as string
        """
        for step in range(max_steps):
            # Build message array for LLM
            messages = [{"role": "system", "content": self.system_message}]
            messages.extend(chat_history)
            messages.append({"role": "user", "content": user_input})

            # Get LLM response
            llm_response = self._call_llm(messages)
            
            # Try to parse as tool call
            tool_call = self._parse_llm_response(llm_response)
            
            if tool_call:
                # Execute the tool call
                result = self._execute_tool_call(tool_call)
                
                if "error" in result:
                    # Return error message
                    error_msg = result["error"]
                    chat_history.append({"role": "assistant", "content": error_msg})
                    return error_msg
                
                # Add tool output to history and continue for natural language response
                tool_output = f"[Tool Output] {result}"
                chat_history.append({"role": "assistant", "content": tool_output})
                continue
            else:
                # Regular response - return it
                chat_history.append({"role": "assistant", "content": llm_response})
                return llm_response

        # Max steps reached
        error_msg = "Max reasoning steps reached without final answer."
        chat_history.append({"role": "assistant", "content": error_msg})
        return error_msg


# ------------------------
# Example Usage
# ------------------------
def main():
    """Example of how to use the SAP Monitoring Agent."""
    # Initialize agent (replace with your actual credentials)
    agent = SAPMonitoringAgent(
        api_key="YOUR_KEY",
        azure_endpoint="https://your-endpoint.openai.azure.com/"
    )
    
    # Conversation history
    chat_history = []

    # Turn 1: Check CPU
    user_input = "Check CPU on hana01"
    print(f"User: {user_input}")
    
    response = agent.chat(user_input, chat_history)
    chat_history.append({"role": "user", "content": user_input})
    print(f"Assistant: {response}")

    # Turn 2: Check memory on same server
    user_input = "Check memory on the same server"
    print(f"\nUser: {user_input}")
    
    response = agent.chat(user_input, chat_history) 
    chat_history.append({"role": "user", "content": user_input})
    print(f"Assistant: {response}")


if __name__ == "__main__":
    main()
