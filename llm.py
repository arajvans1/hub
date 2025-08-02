import requests
import json
from typing import Dict, List, Optional
from langchain_openai import AzureChatOpenAI


class SAPMonitoringAgent:
    """
    An AI agent that helps monitor SAP servers through conversational interface.
    Uses Azure OpenAI via LangChain to understand natural language requests.
    """
    
    def __init__(self, api_key: str, azure_endpoint: str):
        # Configuration
        self.MONITORING_DOMAIN = "mybank.net"
        
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
        
        # Initialize LangChain LLM
        self.llm = AzureChatOpenAI(
            api_key=api_key,
            api_version="2024-08-01",
            azure_endpoint=azure_endpoint,
            model="gpt-4",
        )
         # Build system prompt
        self.system_prompt = self._build_system_prompt()
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt with available commands."""
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
2. Otherwise, respond in plain English."""

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
        context = ""
        
        for step in range(max_steps):
            # Build messages for LangChain
            messages = [{"role": "system", "content": self.system_prompt}]
            
            # Add conversation history
            messages.extend(chat_history)
            
            # Add current context if available
            if context:
                messages.append({"role": "system", "content": f"Current Context: {context}"})
            
            # Add user input
            messages.append({"role": "user", "content": user_input})

            # Get LLM response
            llm_response = self.llm.invoke(messages)
            response_text = llm_response.content.strip()
            
            # Try to parse as tool call
            tool_call = self._parse_llm_response(response_text)
            
            if tool_call:
                # Execute the tool call
                result = self._execute_tool_call(tool_call)
                
                if "error" in result:
                    # Return error message
                    error_msg = result["error"]
                    chat_history.append({"role": "assistant", "content": error_msg})
                    return error_msg
                
                # Add tool result to context for next iteration
                context += f"\nTool called: {tool_call['server']}/{tool_call['command']} {tool_call.get('params', {})} → {result}"
                continue
            else:
                # Regular response - return it
                chat_history.append({"role": "assistant", "content": response_text})
                return response_text

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
    
    # Interactive conversation
    chat_history = []
    print("SAP Monitoring Assistant (type 'exit' to quit)")
    print("=" * 50)
    
    while True:
        user_input = input("\nUser: ")
        if user_input.lower() in ["exit", "quit"]:
            break
            
        response = agent.chat(user_input, chat_history)
        chat_history.append({"role": "user", "content": user_input})
        print(f"Assistant: {response}")


if __name__ == "__main__":
    main()