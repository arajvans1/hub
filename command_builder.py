"""
Command building and validation for SAP Monitoring Platform
"""
from typing import Dict, Any


class CommandBuilder:
    """Handles building and validating monitoring commands."""
    
    def __init__(self, command_specs: Dict[str, Any]):
        self.command_specs = command_specs
    
    def build_command(self, command_spec: Dict[str, Any], params: Dict[str, Any]) -> str:
        """Build the actual command from spec and parameters, applying defaults as needed."""
        base_command = command_spec["agent_command"]
        
        # Merge defaults with provided parameters (provided params override defaults)
        merged_params = dict(command_spec.get("params", {}))
        merged_params.update(params)
        
        # Template substitution for all parameters (defaults + provided)
        # Replace {{.param_name}} with actual values
        for param_name, param_value in merged_params.items():
            placeholder = f"{{{{.{param_name}}}}}"
            base_command = base_command.replace(placeholder, str(param_value))
            
        return base_command
    
    def validate_command(self, command: str, params: Dict[str, Any]) -> bool:
        """Validate command and parameters using required field."""
        if command not in self.command_specs:
            return False
        
        spec = self.command_specs[command]
        required_keys = set(spec.get("required", []))
        provided_keys = set(params.keys())
        
        # Check that all required parameters are provided
        return required_keys.issubset(provided_keys)
        # Note: Optional parameters can be missing - that's perfectly fine!
