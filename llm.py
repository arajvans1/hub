import requests
import json
from typing import Dict, List, Optional
from langchain_openai import AzureChatOpenAI


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
        
        # Simple LLM initialization - only what we need
        self.llm = AzureChatOpenAI(
            api_key=api_key,
            api_version="2024-08-01",
            azure_endpoint=azure_endpoint,
            model="gpt-4",
        )
        
        # Build system prompt once
        self.system_prompt = self._build_system_prompt()
    
    def _build_system_prompt(self) -> str:
        """Build system prompt with available commands - no templates needed!"""
        command_help = "\n".join([
            f"- {cmd}: {spec['description']}, params: {spec['params']}"
            for cmd, spec in self.COMMAND_SPECS.items()
        ])
        
        # Simple string - no LangChain template magic needed
        return f"""You are a SAP Monitoring Assistant.

Available commands:
{command_help}

Instructions:
1. If monitoring is needed, output ONLY JSON:
   {{"action": "monitoring", "server": "<server>", "command": "<command>", "params": {{}} }}
2. Otherwise, respond in plain English."""

    def _call_monitoring_api(self, server: str, command: str, params: Dict = None) -> Dict:
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

    def _validate_command(self, command: str, params: Dict) -> bool:
        """Validate command and parameters."""
        if command not in self.COMMAND_SPECS:
            return False
        expected_keys = set(self.COMMAND_SPECS[command]["params"].keys())
        provided_keys = set(params.keys())
        return expected_keys.issubset(provided_keys)

    def _parse_json_response(self, response: str) -> Optional[Dict]:
        """Parse JSON response - no LangChain parser needed!"""
        try:
            action = json.loads(response)
            if action.get("action") == "monitoring":
                return action
        except json.JSONDecodeError:
            pass
        return None

    def chat(self, user_input: str, max_steps: int = 5) -> str:
        """
        Main chat method - simple and clean!
        
        Args:
            user_input: User's question
            max_steps: Maximum reasoning steps
            
        Returns:
            Assistant's response
        """
        context = ""
        
        for step in range(max_steps):
            # Build messages - no template complexity needed
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_input}
            ]
            
            if context:
                messages.insert(1, {"role": "system", "content": f"Context: {context}"})

            # Get LLM response
            llm_response = self.llm.invoke(messages)
            content = llm_response.content.strip()

            # Try to parse as tool call
            action = self._parse_json_response(content)
            
            if action:
                server = action["server"]
                command = action["command"]
                params = action.get("params", {}) or {}

                # Validate
                if not self._validate_command(command, params):
                    return f"Invalid command or params: {command} {params}"

                # Execute tool
                result = self._call_monitoring_api(server, command, params)
                context += f"\nTool called: {server}/{command} {params} → {result}"
                continue  # Continue reasoning
            else:
                # Final answer
                return content

        return f"Max steps {max_steps} reached without final answer."


# ------------------------
# Simple Usage
# ------------------------
def main():
    """Simple example usage."""
    agent = SAPMonitoringAgent(
        api_key="YOUR_KEY",
        azure_endpoint="https://your-endpoint.openai.azure.com/"
    )
    
    # Test query
    result = agent.chat("Check CPU on hana01 and memory on hana02")
    print(result)


if __name__ == "__main__":
    main()
