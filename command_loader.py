"""
Commands management for SAP Monitoring Platform
"""
import yaml
import os
from typing import Dict, Any


class CommandLoader:
    """Handles loading and validation of YAML command files."""
    
    def __init__(self, commands_file: str = "commands.yaml"):
        self.commands_file = commands_file
        self.commands = self._load_commands()
        
    def _load_commands(self) -> Dict[str, Any]:
        """Load commands from YAML file."""
        try:
            # Get the directory of the current script
            script_dir = os.path.dirname(os.path.abspath(__file__))
            commands_path = os.path.join(script_dir, self.commands_file)
            
            with open(commands_path, 'r') as file:
                commands = yaml.safe_load(file)
                
            # Validate the loaded commands
            self.validate_commands(commands)
            return commands
            
        except FileNotFoundError:
            raise FileNotFoundError(f"Commands file '{self.commands_file}' not found. Please ensure it exists in the same directory as the script.")
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML syntax in commands file: {e}")
        except Exception as e:
            raise RuntimeError(f"Error loading commands: {e}")
    
    def validate_commands(self, commands: Dict[str, Any]) -> None:
        """Validate required sections in commands."""
        if "commands" not in commands:
            raise ValueError("Missing 'commands' section in commands file")
            
        # Validate commands structure
        for cmd_name, cmd_spec in commands["commands"].items():
            required_fields = ["description", "agent_command", "backend"]
            for field in required_fields:
                if field not in cmd_spec:
                    raise ValueError(f"Command '{cmd_name}' missing required field: {field}")
    
    def get_commands(self) -> Dict[str, Any]:
        """Get command specifications."""
        return self.commands["commands"]
    
    def get_command_spec(self, command_name: str) -> Dict[str, Any]:
        """Get a specific command specification by name."""
        return self.commands["commands"].get(command_name, {})
