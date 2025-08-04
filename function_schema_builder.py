"""
OpenAI function schema building for SAP Monitoring Platform
"""
from typing import Dict, Any, List


class FunctionSchemaBuilder:
    """Builds OpenAI function schemas from command specifications."""
    
    def __init__(self, command_specs: Dict[str, Any]):
        self.command_specs = command_specs
    
    def build_function_schemas(self) -> List[Dict[str, Any]]:
        """Build OpenAI function schemas from command specifications."""
        schemas = []
        
        for cmd, spec in self.command_specs.items():
            # Check if this is a SID resolution function
            if spec.get("backend") == "sid_resolver":
                if cmd == "get_available_sids":
                    # get_available_sids doesn't need any parameters
                    param_properties = {}
                    required_params = []
                else:
                    # Other SID functions use 'sid' parameter
                    param_properties = {"sid": {"type": "string", "description": "SAP System ID (e.g., PRD, QAS, DEV, SBX)"}}
                    required_params = ["sid"]
            else:
                # Regular monitoring commands use 'server' parameter
                param_properties = {"server": {"type": "string", "description": "Server hostname to monitor"}}
                required_params = ["server"]
            
            # Add all parameters from params (both required and optional)
            for param_name, default_val in spec.get("params", {}).items():
                is_required = param_name in spec.get("required", [])
                param_properties[param_name] = {
                    "type": "string",
                    "description": f"{'Required' if is_required else 'Optional'} parameter for {cmd} command (default: {default_val})"
                }
            
            # Add only the required parameters to the required array
            required_params.extend(spec.get("required", []))
            
            # Create function schema with command name directly
            schemas.append({
                "type": "function",
                "function": {
                    "name": cmd,
                    "description": f"{spec['description']}",
                    "parameters": {
                        "type": "object",
                        "properties": param_properties,
                        "required": required_params
                    }
                }
            })
        
        return schemas
