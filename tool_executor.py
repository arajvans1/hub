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
        allowed_host_types = command_spec.get("allowed_host_types", [])
        if allowed_host_types:
            host_type = self._determine_host_type(server)
            if host_type not in allowed_host_types:
                # Provide helpful error message with suggestions
                error_msg = f"Command '{function_name}' cannot be executed on {host_type} server '{server}'. "
                error_msg += f"This command is only allowed on: {', '.join(allowed_host_types)} servers."
                
                # Suggest alternative hosts if possible
                alternative_hosts = self._suggest_alternative_hosts(server, allowed_host_types)
                if alternative_hosts:
                    error_msg += f" Try using one of these hosts instead: {', '.join(alternative_hosts)}"
                
                return {"error": error_msg}
        
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
    
    def _determine_host_type(self, hostname: str) -> str:
        """
        Determine if a hostname is an application server or database server.
        
        Args:
            hostname: The hostname to check
            
        Returns:
            'app' for application servers, 'db' for database servers, 'unknown' if not found
        """
        # Check all SIDs in the landscape
        for sid, system_config in self.shared.sid_resolver.landscape_data.items():
            # Check if it's an application server
            app_servers = system_config.get('app_servers', {})
            for server_type, hosts in app_servers.items():
                if isinstance(hosts, list) and hostname in hosts:
                    return 'app'
                elif isinstance(hosts, str) and hostname == hosts:
                    return 'app'
            
            # Check if it's a database server
            database = system_config.get('database', {})
            hana_hosts = database.get('hana_hosts', [])
            if isinstance(hana_hosts, list) and hostname in hana_hosts:
                return 'db'
            elif isinstance(hana_hosts, str) and hostname == hana_hosts:
                return 'db'
        
        return 'unknown'
    
    def _suggest_alternative_hosts(self, current_host: str, allowed_host_types: list) -> list:
        """
        Suggest alternative hosts of the correct type from the same SID.
        
        Args:
            current_host: The hostname that was rejected
            allowed_host_types: List of allowed host types for the command
            
        Returns:
            List of alternative hostnames that could be used
        """
        # Find which SID the current host belongs to
        current_sid = None
        for sid, system_config in self.shared.sid_resolver.landscape_data.items():
            # Check app servers
            app_servers = system_config.get('app_servers', {})
            for server_type, hosts in app_servers.items():
                if isinstance(hosts, list) and current_host in hosts:
                    current_sid = sid
                    break
                elif isinstance(hosts, str) and current_host == hosts:
                    current_sid = sid
                    break
            
            # Check database servers
            if not current_sid:
                database = system_config.get('database', {})
                hana_hosts = database.get('hana_hosts', [])
                if isinstance(hana_hosts, list) and current_host in hana_hosts:
                    current_sid = sid
                    break
                elif isinstance(hana_hosts, str) and current_host == hana_hosts:
                    current_sid = sid
                    break
        
        if not current_sid:
            return []
        
        # Get alternative hosts of the correct type from the same SID
        alternatives = []
        try:
            if 'app' in allowed_host_types:
                app_hosts = self.shared.sid_resolver.get_app_hosts(current_sid)
                alternatives.extend(app_hosts)
            
            if 'db' in allowed_host_types or 'hana' in allowed_host_types:
                db_hosts = self.shared.sid_resolver.get_hana_hosts(current_sid)
                alternatives.extend(db_hosts)
        except ValueError:
            pass  # SID not found, return empty list
        
        # Remove the current host from suggestions and remove duplicates
        alternatives = [host for host in set(alternatives) if host != current_host]
        
        return alternatives[:3]  # Limit to 3 suggestions to keep error message concise
