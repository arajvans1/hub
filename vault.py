"""
Simple Vault Manager for credential management.

Development: Reads from a simple JSON file
Production: Stubs for enterprise vault integration
"""

import json
from pathlib import Path
from typing import Dict, Optional


class VaultError(Exception):
    """Custom exception for vault operations."""
    pass


class VaultManager:
    """
    Simple vault manager that reads from file in development.
    Production integration is stubbed for enterprise vault.
    """
    
    def __init__(self, vault_file: str = "config/vault.json"):
        """
        Initialize vault manager.
        
        Args:
            vault_file: Path to the vault file (development only)
        """
        self.vault_file = Path(vault_file)
        self.vault_data = {}
        self._load_vault()
    
    def _load_vault(self) -> None:
        """Load vault data from file (development) or call enterprise vault (production)."""
        # For development: read from simple JSON file
        if self.vault_file.exists():
            try:
                with open(self.vault_file, 'r') as f:
                    self.vault_data = json.load(f)
                print(f"Loaded vault from {self.vault_file}")
            except Exception as e:
                print(f"Warning: Could not load vault file {self.vault_file}: {e}")
                self.vault_data = {}
        else:
            print(f"Vault file {self.vault_file} not found. Use setup to create it.")
            self.vault_data = {}
        
        # TODO: Production implementation
        # For production: replace with enterprise vault API calls
        # self._load_from_enterprise_vault()
    
    def _load_from_enterprise_vault(self) -> None:
        """
        STUB: Load secrets from enterprise vault.
        
        In production, this would make API calls to your enterprise vault:
        - Azure Key Vault
        - HashiCorp Vault  
        - AWS Secrets Manager
        - etc.
        """
        # Example implementation for Azure Key Vault:
        # from azure.keyvault.secrets import SecretClient
        # from azure.identity import DefaultAzureCredential
        # 
        # credential = DefaultAzureCredential()
        # client = SecretClient(vault_url="https://your-vault.vault.azure.net/", credential=credential)
        # 
        # self.vault_data = {
        #     "azure_openai_api_key": client.get_secret("azure-openai-api-key").value,
        #     "azure_openai_endpoint": client.get_secret("azure-openai-endpoint").value
        # }
        
        raise NotImplementedError("Enterprise vault integration not implemented yet")
    
    def get_secret(self, key: str) -> str:
        """
        Get a secret from the vault.
        
        Args:
            key: Secret identifier
            
        Returns:
            Secret value
            
        Raises:
            VaultError: If secret not found
        """
        if key not in self.vault_data:
            raise VaultError(f"Secret '{key}' not found in vault")
        
        return self.vault_data[key]
    
    def get_azure_openai_config(self) -> Dict[str, str]:
        """
        Get Azure OpenAI configuration from vault.
        
        Returns:
            Dictionary with api_key and azure_endpoint
        """
        try:
            api_key = self.get_secret("azure_openai_api_key")
            azure_endpoint = self.get_secret("azure_openai_endpoint")
            
            return {
                "api_key": api_key,
                "azure_endpoint": azure_endpoint
            }
        except VaultError as e:
            raise VaultError(f"Failed to get Azure OpenAI config: {e}")
    
    def list_secrets(self) -> list:
        """List all secret keys (not values) in the vault."""
        return list(self.vault_data.keys())


# Convenience function for quick access
def get_vault_manager() -> VaultManager:
    """Get a vault manager instance."""
    return VaultManager()


if __name__ == "__main__":
    # Demo/testing functionality
    print("=== Simple Vault Demo ===")
    
    try:
        vault_manager = get_vault_manager()
        
        # Test retrieval
        try:
            azure_config = vault_manager.get_azure_openai_config()
            print(f"\nAzure OpenAI configured: ✅")
            print(f"Endpoint: {azure_config['azure_endpoint']}")
            print(f"API Key: {'*' * (len(azure_config['api_key']) - 4) + azure_config['api_key'][-4:] if azure_config['api_key'] else 'Not set'}")
        except VaultError as e:
            print(f"\nAzure OpenAI config: ❌ {e}")
            print("Create config/vault.json with your credentials")
        
        print(f"\nAvailable secrets: {vault_manager.list_secrets()}")
        
    except Exception as e:
        print(f"Vault demo failed: {e}")
