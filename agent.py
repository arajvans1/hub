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
            
            # Check for HTTP errors (404, 500, etc.)
            if response.status_code != 200:
                return {
                    "error": f"HTTP {response.status_code}: {response.reason}",
                    "details": response.text if response.text else "No additional details"
                }
            
            # Try to parse JSON response
            try:
                return response.json()
            except ValueError as json_error:
                return {
                    "error": f"Invalid JSON response from agent",
                    "details": f"JSON parse error: {str(json_error)}",
                    "raw_response": response.text[:200]  # First 200 chars
                }
            
        except requests.exceptions.RequestException as e:
            return {"error": f"Network error: {str(e)}"}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}
    
    def discover_agent(self, server: str) -> str:
        """Discover the appropriate agent for a server. Future implementation."""
        # TODO: Implement proper agent discovery logic
        # This could query a service registry, DNS, or configuration
        return f"http://{server}.{self.monitoring_domain}:8090"
