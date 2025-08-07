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
            
            # Process agent_command fields - resolve file references
            self._resolve_command_files(commands, script_dir)
            
            return commands
            
        except FileNotFoundError:
            raise FileNotFoundError(f"Commands file '{self.commands_file}' not found. Please ensure it exists in the same directory as the script.")
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML syntax in commands file: {e}")
        except Exception as e:
            raise RuntimeError(f"Error loading commands: {e}")
    
    def _resolve_command_files(self, commands: Dict[str, Any], base_dir: str) -> None:
        """Resolve file references in agent_command fields."""
        for cmd_name, cmd_spec in commands["commands"].items():
            agent_command = cmd_spec.get("agent_command", "")
            
            # Only support string format: "file:path/to/file"
            if isinstance(agent_command, str) and agent_command.startswith("file:"):
                file_path = agent_command[5:]  # Remove "file:" prefix
                cmd_spec["agent_command"] = self._load_command_file(file_path, base_dir, cmd_name)
    
    def _load_command_file(self, file_path: str, base_dir: str, cmd_name: str) -> str:
        """Load command content from file."""
        try:
            # Support both absolute and relative paths
            if os.path.isabs(file_path):
                full_path = file_path
            else:
                # For relative paths, always resolve from the script directory
                # This ensures consistent behavior regardless of working directory
                full_path = os.path.join(base_dir, file_path)
            
            with open(full_path, 'r', encoding='utf-8') as file:
                content = file.read().strip()
            
            print(f"Loaded command '{cmd_name}' from file: {file_path}")
            return content
            
        except FileNotFoundError:
            # Provide helpful error message showing expected location
            if not os.path.isabs(file_path):
                expected_path = os.path.join(base_dir, file_path)
                raise FileNotFoundError(f"Command file '{file_path}' not found for command '{cmd_name}'. Expected at: {expected_path}")
            else:
                raise FileNotFoundError(f"Command file '{file_path}' not found for command '{cmd_name}'")
        except Exception as e:
            raise RuntimeError(f"Error loading command file '{file_path}' for command '{cmd_name}': {e}")
    
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
            
            # Validate agent_command format
            agent_command = cmd_spec["agent_command"]
            if not isinstance(agent_command, str):
                raise ValueError(f"Command '{cmd_name}' agent_command must be a string")
    
    def get_commands(self) -> Dict[str, Any]:
        """Get command specifications."""
        return self.commands["commands"]
    
    def get_command_spec(self, command_name: str) -> Dict[str, Any]:
        """Get a specific command specification by name."""
        return self.commands["commands"].get(command_name, {})
