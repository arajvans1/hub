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

        # Check if command has host type restrictions
        allowed_host_types = command_spec.get("allowed_host_types", "all")

        # Find which SID this host belongs to (even for "all" commands, we need to validate the host exists)
        sid = self.shared.sid_resolver.find_sid_by_host(server)

        if not sid:
            return {"error": f"Server '{server}' not found in landscape configuration"}

        # If "all" is allowed, we've already validated the host exists, so proceed
        if allowed_host_types != "all":
            # Get appropriate hosts based on allowed type
            try:
                if allowed_host_types == "app":
                    valid_hosts = self.shared.sid_resolver.get_app_hosts(sid)
                    host_type_description = "application"
                elif allowed_host_types == "db":
                    valid_hosts = self.shared.sid_resolver.get_hana_hosts(sid)
                    host_type_description = "database"
                else:
                    return {"error": f"Invalid allowed_host_types value: {allowed_host_types}"}

                # Check if the provided server is in the valid hosts list
                if server not in valid_hosts:
                    error_msg = f"Command '{function_name}' can only be executed on {host_type_description} servers. "
                    error_msg += f"Server '{server}' is not a {host_type_description} server for SID '{sid}'. "

                    if valid_hosts:
                        error_msg += f"Try using one of these {host_type_description} servers instead: {', '.join(valid_hosts)}"
                    else:
                        error_msg += f"No {host_type_description} servers found for SID '{sid}'"

                    return {"error": error_msg}

            except ValueError as e:
                return {"error": f"Failed to validate host type: {str(e)}"}

        # Validate command exists and parameters are valid using ALL function arguments
        # (including server, since it may be listed as required in command spec)
        if not self.shared.command_builder.validate_command(function_name, function_args):
            return {"error": f"Invalid command '{function_name}' or parameters: {function_args}"}

        # Build the actual command using shared command builder
        # (server won't be substituted since command templates don't use {{.server}})
        actual_command = self.shared.command_builder.build_command(command_spec, function_args)

        # Parse backend to determine executor and backend type
        backend = command_spec.get("backend", "shell")

        # Support hybrid execution: "ansible.shell" or "agent.soap" or just "shell" (backward compat)
        if "." in backend:
            executor, backend_type = backend.split(".", 1)
        else:
            # Backward compatibility: no prefix defaults to agent
            executor = "agent"
            backend_type = backend

        # Route to appropriate executor
        try:
            if executor == "ansible":
                # Use Ansible executor
                result = self.shared.ansible_executor.execute(
                    server=server,
                    command=actual_command,
                    backend=backend_type,
                    timeout=command_spec.get("timeout", 30)
                )
            elif executor == "agent":
                # Use Go agent
                result = self.shared.agent.call_agent_api(
                    server=server,
                    command=actual_command,
                    backend=backend_type,
                    timeout=command_spec.get("timeout", 30)
                )
            else:
                return {"error": f"Unknown executor: {executor}. Use 'ansible' or 'agent'"}

            return result

        except Exception as e:
            return {"error": f"{executor.capitalize()} execution failed: {str(e)}"}
