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
            param_properties = {}
            
            # Add standard parameter descriptions for common parameters
            standard_params = {
                "sid": {
                    "type": "string", 
                    "description": "SAP System ID (e.g., PRD, QAS, DEV, SBX)"
                },
                "server": {
                    "type": "string", 
                    "description": "Server hostname to monitor"
                }
            }
            
            # Add required parameters with standard descriptions if available
            for param_name in spec.get("required", []):
                if param_name in standard_params:
                    param_properties[param_name] = standard_params[param_name]
                else:
                    param_properties[param_name] = {
                        "type": "string",
                        "description": f"Required parameter for {cmd} command"
                    }
            
            # Add optional parameters from params section
            for param_name, default_val in spec.get("params", {}).items():
                if param_name not in param_properties:  # Don't overwrite required params
                    param_properties[param_name] = {
                        "type": "string",
                        "description": f"Optional parameter for {cmd} command (default: {default_val})"
                    }
            
            # Create function schema
            schemas.append({
                "type": "function",
                "function": {
                    "name": cmd,
                    "description": spec['description'],
                    "parameters": {
                        "type": "object",
                        "properties": param_properties,
                        "required": spec.get("required", [])
                    }
                }
            })
        
        return schemas
