"""
Agent communication for SAP Monitoring Platform
"""
import requests
from typing import Dict, Any


class Agent:
    """Handles communication with monitoring agents."""
    
    def __init__(self, monitoring_domain: str):
        self.monitoring_domain = monitoring_domain
    
    def call_agent_api(self, server: str, command: str, backend: str, timeout: int = 30) -> Dict[str, Any]:
        """Execute monitoring command using improved architecture."""
        try:
            # Simple agent URL construction (no discovery yet)
            url = f"http://{server}.{self.monitoring_domain}:8090/execute"
            
            # Send constructed command to agent (new payload format)
            payload = {
                "command": command,
                "backend": backend,
                "timeout": timeout
            }
            
            response = requests.post(url, json=payload, timeout=5)
            return response.json()
            
        except Exception as e:
            return {"error": str(e)}
    
    def discover_agent(self, server: str) -> str:
        """Discover the appropriate agent for a server. Future implementation."""
        # TODO: Implement proper agent discovery logic
        # This could query a service registry, DNS, or configuration
        return f"http://{server}.{self.monitoring_domain}:8090"
