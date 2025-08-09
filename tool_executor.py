"""
Tool execution logic for SAP Monitoring Platform
"""
from typing import Dict, Any


class ToolExecutor:
    """Handles execution of function tool calls for both SID functions and monitoring commands."""
    
    def __init__(self, shared_resources):
        """
        Initialize tool executor with shared resources.
        
        Args:
            shared_resources: SharedResources instance with all shared objects
        """
        self.shared = shared_resources
    
    def execute_tool_call(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a function tool call - handles both SID functions and monitoring commands"""
        function_name = tool_call["name"]
        function_args = tool_call["args"]  # Already a dict, no need to json.loads()
        
        # Get command specification from CommandLoader
        command_spec = self.shared.commands_loader.get_command_spec(function_name)
        if not command_spec:
            return {"error": f"Unknown command: {function_name}"}
        
        # Route to appropriate handler based on backend
        backend = command_spec.get("backend")
        
        if backend == "sid_resolver":
            return self._execute_sid_function(function_name, function_args)
        else:
            return self._execute_monitoring_command(function_name, function_args, command_spec)
    
    def _execute_sid_function(self, function_name: str, function_args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute SID resolution functions."""
        try:
            if function_name == "get_available_sids":
                available_sids = self.shared.sid_resolver.get_available_sids()
                return {
                    "function": function_name,
                    "available_sids": available_sids,
                    "count": len(available_sids)
                }
            elif function_name == "get_all_hosts":
                sid = function_args.get("sid")
                if not sid:
                    return {"error": "SID parameter is required"}
                hosts = self.shared.sid_resolver.get_all_hosts(sid)
            elif function_name == "get_app_hosts":
                sid = function_args.get("sid")
                if not sid:
                    return {"error": "SID parameter is required"}
                hosts = self.shared.sid_resolver.get_app_hosts(sid)
            elif function_name == "get_hana_hosts":
                sid = function_args.get("sid")
                if not sid:
                    return {"error": "SID parameter is required"}
                hosts = self.shared.sid_resolver.get_hana_hosts(sid)
            else:
                return {"error": f"Unknown SID function: {function_name}"}
            
            # For functions that return hosts
            if function_name != "get_available_sids":
                return {
                    "sid": sid,
                    "function": function_name,
                    "hosts": hosts,
                    "count": len(hosts)
                }
                
        except Exception as e:
            return {"error": f"Failed to execute SID function '{function_name}': {str(e)}"}
    
    def _execute_monitoring_command(self, function_name: str, function_args: Dict[str, Any], 
                                   command_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Execute regular monitoring commands."""
        # Check for required server parameter
        server = function_args.get("server")
        if not server:
            return {"error": "Server parameter is required for monitoring commands"}
        
        # Validate command exists and parameters are valid using ALL function arguments
        # (including server, since it may be listed as required in command spec)
        if not self.shared.command_builder.validate_command(function_name, function_args):
            return {"error": f"Invalid command '{function_name}' or parameters: {function_args}"}
        
        # Build the actual command using shared command builder
        # (server won't be substituted since command templates don't use {{.server}})
        actual_command = self.shared.command_builder.build_command(command_spec, function_args)
        
        # Execute monitoring command via shared agent with error handling
        try:
            result = self.shared.agent.call_agent_api(
                server=server,
                command=actual_command,
                backend=command_spec["backend"],
                timeout=command_spec.get("timeout", 30)
            )
            
            return result
            
        except Exception as e:
            return {"error": f"Agent API call failed: {str(e)}"}
