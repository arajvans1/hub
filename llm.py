import json
from typing import List, Dict, Any
from pathlib import Path
from langchain_openai import AzureChatOpenAI

from command_loader import CommandLoader
from command_builder import CommandBuilder
from agent import Agent
from ansible_executor import AnsibleExecutor
from function_schema_builder import FunctionSchemaBuilder
from sid_resolver import SIDResolver
from vault import VaultManager, VaultError
from tool_executor import ToolExecutor


# Shared singletons - created once and reused
class SharedResources:
    """Simple container for shared resources - no fancy singleton pattern"""
    def __init__(self):
        self.commands_loader = None
        self.command_builder = None
        self.agent = None
        self.ansible_executor = None
        self.function_schema_builder = None
        self.sid_resolver = None
        self.vault_manager = None
        self.tools = None
        self.system_prompt = None
        self.initialized = False
    
    def initialize(self, 
                   commands_file: str = "config/commands.yaml",
                   landscape_file: str = "config/landscape.json",
                   system_prompt_file: str = "config/system_prompt"):
        """Initialize all shared resources"""
        if self.initialized:
            return
        
        # Initialize vault manager first (other components may need secrets)
        try:
            self.vault_manager = VaultManager()
            print("Vault manager initialized")
        except VaultError as e:
            print(f"Warning: Vault initialization failed: {e}")
            print("Continuing without vault - credentials must be provided manually")
            self.vault_manager = None
            
        # Create shared objects once
        self.commands_loader = CommandLoader(commands_file)
        commands = self.commands_loader.get_commands()

        # Initialize SID resolver for landscape management
        self.sid_resolver = SIDResolver(landscape_file)

        # Hard-coded monitoring domain (not part of function schemas)
        monitoring_domain = "mybank.net"

        self.command_builder = CommandBuilder(commands)
        self.agent = Agent(monitoring_domain)

        # Initialize Ansible executor for hybrid execution model
        try:
            self.ansible_executor = AnsibleExecutor(inventory_file="config/ansible_inventory.ini")
            print("Ansible executor initialized")
        except Exception as e:
            print(f"Warning: Ansible executor initialization failed: {e}")
            print("Ansible-based commands will not be available. Go agent will be used as fallback.")
            self.ansible_executor = None

        self.function_schema_builder = FunctionSchemaBuilder(commands)
        self.tools = self.function_schema_builder.build_function_schemas()
        
        # Load system prompt from config file
        self.system_prompt = self._load_system_prompt(system_prompt_file)
        
        self.initialized = True
        print(f"Shared resources initialized with {len(commands)} commands")
    
    def get_azure_openai_credentials(self) -> Dict[str, str]:
        """
        Get Azure OpenAI credentials from vault or return empty dict for manual configuration.

        Returns:
            Dictionary with api_key and azure_endpoint, or empty dict if vault unavailable
        """
        if self.vault_manager:
            try:
                return self.vault_manager.get_azure_openai_config()
            except VaultError as e:
                print(f"Warning: Could not retrieve Azure OpenAI credentials from vault: {e}")

        # Return empty dict if vault unavailable - allows testing without Azure OpenAI
        print("Note: Running without Azure OpenAI credentials (test mode)")
        return {}
    
    def _load_system_prompt(self, system_prompt_file: str) -> str:
        """Load system prompt from config file."""
        try:
            # Get the directory of the current script
            script_dir = Path(__file__).parent
            prompt_path = script_dir / system_prompt_file
            
            with open(prompt_path, 'r', encoding='utf-8') as file:
                prompt_content = file.read().strip()
            
            print(f"Loaded system prompt from {prompt_path}")
            return prompt_content
            
        except FileNotFoundError:
            error_msg = f"System prompt file not found: {system_prompt_file}"
            print(f"Warning: {error_msg}")
            # Fallback to a basic prompt
            return "You are a SAP S/4HANA Monitoring Assistant. Use the available functions to help monitor SAP systems."
        except Exception as e:
            error_msg = f"Error loading system prompt: {e}"
            print(f"Warning: {error_msg}")
            # Fallback to a basic prompt
            return "You are a SAP S/4HANA Monitoring Assistant. Use the available functions to help monitor SAP systems."


class SAPMonitoringAgent:
    """
    Lightweight SAP monitoring agent that uses explicitly passed shared resources.
    """
    
    def __init__(self, shared_resources: SharedResources):
        """
        Initialize agent with explicitly passed shared resources.
        
        Args:
            shared_resources: SharedResources instance with all shared objects
        """
        if not shared_resources.initialized:
            raise RuntimeError("SharedResources not initialized!")
            
        # Store reference to shared resources
        self.shared = shared_resources
        
        # Get credentials from vault
        vault_credentials = self.shared.get_azure_openai_credentials()
        
        if not vault_credentials:
            raise RuntimeError("No Azure OpenAI credentials found in vault")
        
        # Only create the LLM client per agent
        self.llm = AzureChatOpenAI(
            api_key=vault_credentials["api_key"],
            api_version="2024-08-01",
            azure_endpoint=vault_credentials["azure_endpoint"],
            model="gpt-4",
            max_retries=3,
            timeout=30,
        )
        
        # Direct access to shared resources
        self.tools = self.shared.tools
        self.system_prompt = self.shared.system_prompt
        
        # Initialize tool executor
        self.tool_executor = ToolExecutor(self.shared)
    
    def _execute_tool_call(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a function tool call using the dedicated ToolExecutor."""
        return self.tool_executor.execute_tool_call(tool_call)

    def chat(self, chat_history: List[dict], max_steps: int = 3) -> str:
        """        Main chat method using OpenAI function calling - much more robust!
        Args:
            chat_history: Conversation messages including current user input
            max_steps: Maximum reasoning steps
            
        Returns:
            Assistant's response
        """
        # Build messages from chat history
        messages = list(chat_history)  # Copy chat history

        final_response = None
        
        for step in range(max_steps):
            # Get LLM response with function calling capability
            try:
                llm_response = self.llm.invoke(
                    messages, 
                    tools=self.tools,
                    tool_choice="auto"  # Let LLM decide when to use tools
                )
                content = llm_response.content.strip() if llm_response.content else ""
                tool_calls = llm_response.tool_calls or []
                
            except Exception as e:
                final_response = f"Error communicating with AI service: {str(e)}"
                break
            
            # Add assistant message to working messages
            assistant_msg = {"role": "assistant", "content": content}
            if tool_calls:
                assistant_msg["tool_calls"] = [
                    {
                        "id": tc["id"],
                        "type": "function", 
                        "function": {"name": tc["name"], "arguments": tc["args"]}
                    } for tc in tool_calls
                ]
            messages.append(assistant_msg)
            
            # Process any tool calls - NOW WITH PARALLEL EXECUTION!
            if tool_calls:
                from concurrent.futures import ThreadPoolExecutor, as_completed
                
                with ThreadPoolExecutor(max_workers=3) as executor:
                    # Submit all tool calls for parallel execution
                    future_to_tool = {
                        executor.submit(self._execute_tool_call, tool_call): tool_call
                        for tool_call in tool_calls
                    }
                    
                    # Collect results as they complete
                    for future in as_completed(future_to_tool):
                        tool_call = future_to_tool[future]
                        try:
                            result = future.result()
                        except Exception as e:
                            # Handle errors gracefully
                            result = {"error": str(e)}
                        
                        # Add tool result to working messages (unified for both success and error)
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "content": json.dumps(result)
                        })
            
            # If we processed tool calls, continue to next step for final response
            # If no tool calls, this is our final response
            if tool_calls:
                continue
            else:
                final_response = content
                break

        # If we hit max steps without a final response, return error
        if final_response is None:
            final_response = f"Unable to complete request within {max_steps} steps. Please try a simpler request."

        # Add only the final response to chat history (not tool call details)
        chat_history.append({"role": "assistant", "content": final_response})
        return final_response

# ------------------------
# Usage Examples
# ------------------------
def main():
    """Interactive SAP monitoring chat interface."""
    
    # Create shared resources ONCE - you can clearly see what's being created
    print("Creating shared resources...")
    shared_resources = SharedResources()
    
    # Initialize shared resources ONCE at startup
    try:
        shared_resources.initialize(
            commands_file="config/commands.yaml",
            landscape_file="config/landscape.json",
            system_prompt_file="config/system_prompt"
        )
    except Exception as e:
        print(f"Failed to initialize shared resources: {e}")
        print("\nPlease ensure:")
        print("1. PyYAML is installed: pip install pyyaml")
        print("2. config/commands.yaml exists")
        print("3. config/landscape.json exists")
        print("4. config/system_prompt.txt exists")
        return
    
    # Now create lightweight agent - vault credentials will be used automatically
    try:
        agent = SAPMonitoringAgent(shared_resources=shared_resources)
        
        print("=== SAP S/4HANA Monitoring Assistant ===")
        print(f"Loaded {len(shared_resources.commands_loader.get_commands())} monitoring commands")
        print(f"Available SAP Systems (SIDs): {', '.join(shared_resources.sid_resolver.get_available_sids())}")
        print("\nType your monitoring requests or 'quit' to exit")
        print("Examples:")
        print("  - 'Check status of server01' (direct hostname)")
        print("  - 'show available SIDs'")
        print("-" * 60)
        
    except Exception as e:
        print(f"Failed to initialize SAP Monitoring Agent: {e}")
        print("Please ensure your vault.json has correct Azure OpenAI credentials")
        return
    
    # Initialize chat history with system prompt (added once!)
    chat_history = [{"role": "system", "content": agent.system_prompt}]
    
    while True:
        try:
            user_input = input("\n> ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("Goodbye!")
                break
                
            if not user_input:
                continue
                
            # Add user input to chat history BEFORE calling chat
            chat_history.append({"role": "user", "content": user_input})
            
            # Keep chat history manageable (last 20 messages + system prompt)
            if len(chat_history) > 21:  # system + 20 messages
                chat_history = [chat_history[0]] + chat_history[-20:]  # Keep system + last 20
            
            # Get response - no need to pass user_input separately!
            response = agent.chat(chat_history)
            print(f"\nAssistant: {response}")
            
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}")
            print("Please try again.")


if __name__ == "__main__":
    main()
