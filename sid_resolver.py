"""
SID Resolver for SAP S/4HANA Monitoring System.

Provides the 3 core functions that the LLM will call:
1. get_all_hosts - Returns all hosts (app + DB) for a SID
2. get_app_hosts - Returns only application server hosts  
3. get_hana_hosts - Returns HANA DB nodes
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Union


class SIDResolver:
    """
    SAP System ID resolver with 3 core functions for LLM function calling.
    
    This is the ONLY place that should contain SID resolution logic.
    """
    
    def __init__(self, landscape_config_path: Union[str, Path]):
        """
        Initialize the SID resolver with landscape configuration.
        
        Args:
            landscape_config_path: Path to the landscape.json configuration file
        """
        self.landscape_config_path = Path(landscape_config_path)
        self.landscape_data: Dict[str, Any] = {}
        self.logger = logging.getLogger(__name__)
        
        self._load_landscape_config()
    
    def _load_landscape_config(self) -> None:
        """Load and validate the landscape configuration."""
        try:
            with open(self.landscape_config_path, 'r', encoding='utf-8') as file:
                self.landscape_data = json.load(file)
            
            self.logger.info(f"Loaded landscape configuration from {self.landscape_config_path}")
            
        except FileNotFoundError:
            error_msg = f"Landscape configuration file not found: {self.landscape_config_path}"
            self.logger.error(error_msg)
            raise FileNotFoundError(error_msg)
        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON in landscape configuration: {e}"
            self.logger.error(error_msg)
            raise ValueError(error_msg)
    
    # =====================================
    # CORE FUNCTIONS FOR LLM FUNCTION CALLING
    # =====================================
    
    def get_all_hosts(self, sid: str) -> List[str]:
        """
        Get all hosts (application + database) for a SAP SID.
        
        This is Function 1 that the LLM will call.
        
        Args:
            sid: SAP System ID (e.g., 'PRD', 'QAS', 'DEV')
            
        Returns:
            List of all hostnames for the SID
            
        Raises:
            ValueError: If SID not found
        """
        if sid not in self.landscape_data:
            raise ValueError(f"SID '{sid}' not found in landscape configuration")
        
        system = self.landscape_data[sid]
        all_hosts = []
        
        # Get all application server hosts
        app_servers = system.get('app_servers', {})
        for server_type, hosts in app_servers.items():
            if isinstance(hosts, list):
                all_hosts.extend(hosts)
            elif isinstance(hosts, str):
                all_hosts.append(hosts)
        
        # Get database hosts
        database = system.get('database', {})
        hana_hosts = database.get('hana_hosts', [])
        if isinstance(hana_hosts, list):
            all_hosts.extend(hana_hosts)
        elif isinstance(hana_hosts, str):
            all_hosts.append(hana_hosts)
        
        return list(set(all_hosts))  # Remove duplicates
    
    def get_app_hosts(self, sid: str) -> List[str]:
        """
        Get only application server hosts for a SAP SID.
        
        This is Function 2 that the LLM will call.
        
        Args:
            sid: SAP System ID
            
        Returns:
            List of application server hostnames
            
        Raises:
            ValueError: If SID not found
        """
        if sid not in self.landscape_data:
            raise ValueError(f"SID '{sid}' not found in landscape configuration")
        
        system = self.landscape_data[sid]
        app_hosts = []
        
        app_servers = system.get('app_servers', {})
        for server_type, hosts in app_servers.items():
            if isinstance(hosts, list):
                app_hosts.extend(hosts)
            elif isinstance(hosts, str):
                app_hosts.append(hosts)
        
        return app_hosts
    
    def get_hana_hosts(self, sid: str) -> List[str]:
        """
        Get HANA database hosts for a SAP SID.
        
        This is Function 3 that the LLM will call.
        
        Args:
            sid: SAP System ID
            
        Returns:
            List of HANA database hostnames
            
        Raises:
            ValueError: If SID not found
        """
        if sid not in self.landscape_data:
            raise ValueError(f"SID '{sid}' not found in landscape configuration")
        
        system = self.landscape_data[sid]
        database = system.get('database', {})
        hana_hosts = database.get('hana_hosts', [])
        
        if isinstance(hana_hosts, str):
            return [hana_hosts]
        elif isinstance(hana_hosts, list):
            return hana_hosts
        else:
            return []
    
    # =====================================
    # UTILITY FUNCTIONS (NOT FOR LLM)
    # =====================================
    
    def get_available_sids(self) -> List[str]:
        """Get all available SIDs - for CLI/debugging only."""
        return list(self.landscape_data.keys())
    
    def get_system_info(self, sid: str) -> Dict[str, Any]:
        """Get complete system information - for CLI/debugging only."""
        if sid not in self.landscape_data:
            raise ValueError(f"SID '{sid}' not found")
        return self.landscape_data[sid].copy()
    
    def validate_sid(self, sid: str) -> bool:
        """Check if SID exists - for validation only."""
        return sid in self.landscape_data
    
    def get_primary_host(self, sid: str, prefer_type: str = "pas") -> str:
        """
        Get the primary host for a SID.
        
        Args:
            sid: SAP System ID
            prefer_type: Preferred server type ('pas', 'ascs', 'aas')
            
        Returns:
            Primary hostname
        """
        app_hosts = self.get_app_hosts(sid)
        if not app_hosts:
            raise ValueError(f"No application hosts found for SID '{sid}'")
        
        # Try to get the preferred type first
        system = self.landscape_data[sid]
        app_servers = system.get('app_servers', {})
        
        if prefer_type in app_servers and app_servers[prefer_type]:
            preferred_hosts = app_servers[prefer_type]
            if isinstance(preferred_hosts, list) and preferred_hosts:
                return preferred_hosts[0]
            elif isinstance(preferred_hosts, str):
                return preferred_hosts
        
        # Fallback to first available host
        return app_hosts[0]
    
    def reload_config(self) -> None:
        """Reload the landscape configuration from file."""
        self._load_landscape_config()
        self.logger.info("Landscape configuration reloaded")

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Union


class SIDResolver:
    """
    Resolves SAP System IDs (SIDs) to hostnames and connection information.
    
    This class loads the SAP landscape configuration and provides methods to:
    - Resolve SIDs to specific hosts
    - Get connection information for systems
    - Handle fallback scenarios for host resolution
    """
    
    def __init__(self, landscape_config_path: Union[str, Path]):
        """
        Initialize the SID resolver with landscape configuration.
        
        Args:
            landscape_config_path: Path to the landscape.json configuration file
            
        Raises:
            FileNotFoundError: If the landscape configuration file doesn't exist
            ValueError: If the configuration is invalid
        """
        self.landscape_config_path = Path(landscape_config_path)
        self.landscape_data: Dict[str, Any] = {}
        self.logger = logging.getLogger(__name__)
        
        self._load_landscape_config()
    
    def _load_landscape_config(self) -> None:
        """Load and validate the landscape configuration."""
        try:
            with open(self.landscape_config_path, 'r', encoding='utf-8') as file:
                self.landscape_data = json.load(file)
            
            self._validate_config()
            self.logger.info(f"Loaded landscape configuration from {self.landscape_config_path}")
            
        except FileNotFoundError:
            error_msg = f"Landscape configuration file not found: {self.landscape_config_path}"
            self.logger.error(error_msg)
            raise FileNotFoundError(error_msg)
        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON in landscape configuration: {e}"
            self.logger.error(error_msg)
            raise ValueError(error_msg)
    
    def _validate_config(self) -> None:
        """Validate the structure of the landscape configuration."""
        required_keys = ['landscape', 'defaults']
        for key in required_keys:
            if key not in self.landscape_data:
                raise ValueError(f"Missing required key '{key}' in landscape configuration")
        
        if not isinstance(self.landscape_data['landscape'], dict):
            raise ValueError("'landscape' must be a dictionary")
    
    def get_available_sids(self) -> List[str]:
        """
        Get all available SIDs from the landscape configuration.
        
        Returns:
            List of available SID names
        """
        sids = []
        for environment in self.landscape_data['landscape'].values():
            if isinstance(environment, dict):
                sids.extend(environment.keys())
        return sorted(sids)
    
    def get_environments(self) -> List[str]:
        """
        Get all available environments from the landscape configuration.
        
        Returns:
            List of environment names (e.g., 'development', 'sandbox')
        """
        return list(self.landscape_data['landscape'].keys())
    
    def resolve_sid_to_hosts(self, sid: str, host_type: Optional[str] = None) -> List[str]:
        """
        Resolve a SID to a list of hostnames.
        
        Args:
            sid: The SAP System ID to resolve
            host_type: Specific host type to return ('application_servers', 'database_server', 'web_dispatcher')
                      If None, uses the preferred host type from defaults
        
        Returns:
            List of hostnames for the specified SID and host type
            
        Raises:
            ValueError: If the SID is not found or host type is invalid
        """
        system_info = self._find_system_by_sid(sid)
        if not system_info:
            raise ValueError(f"SID '{sid}' not found in landscape configuration")
        
        hosts = system_info.get('hosts', {})
        if not hosts:
            raise ValueError(f"No hosts configured for SID '{sid}'")
        
        # Use provided host_type or fall back to default
        if host_type is None:
            host_type = self.landscape_data['defaults'].get('preferred_host_type', 'application_servers')
        
        # Get hosts for the specified type
        if host_type in hosts:
            host_list = hosts[host_type]
            # Handle both single host (string) and multiple hosts (list)
            if isinstance(host_list, str):
                return [host_list]
            elif isinstance(host_list, list):
                return host_list
            else:
                raise ValueError(f"Invalid host configuration for SID '{sid}', host type '{host_type}'")
        
        # Try fallback host types
        fallback_types = self.landscape_data['defaults'].get('fallback_host_types', [])
        for fallback_type in fallback_types:
            if fallback_type in hosts:
                host_list = hosts[fallback_type]
                if isinstance(host_list, str):
                    return [host_list]
                elif isinstance(host_list, list):
                    return host_list
        
        raise ValueError(f"No hosts found for SID '{sid}' with host type '{host_type}' or fallback types")
    
    def get_primary_host(self, sid: str, host_type: Optional[str] = None) -> str:
        """
        Get the primary (first) host for a SID.
        
        Args:
            sid: The SAP System ID to resolve
            host_type: Specific host type to return
        
        Returns:
            Primary hostname for the SID
            
        Raises:
            ValueError: If no hosts are found for the SID
        """
        hosts = self.resolve_sid_to_hosts(sid, host_type)
        if not hosts:
            raise ValueError(f"No hosts found for SID '{sid}'")
        return hosts[0]
    
    def get_system_info(self, sid: str) -> Dict[str, Any]:
        """
        Get complete system information for a SID.
        
        Args:
            sid: The SAP System ID
            
        Returns:
            Dictionary containing all system information (hosts, ports, client, etc.)
            
        Raises:
            ValueError: If the SID is not found
        """
        system_info = self._find_system_by_sid(sid)
        if not system_info:
            raise ValueError(f"SID '{sid}' not found in landscape configuration")
        
        return system_info.copy()
    
    def get_connection_info(self, sid: str, host_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Get connection information for a SID including host, ports, and client.
        
        Args:
            sid: The SAP System ID
            host_type: Specific host type for connection
            
        Returns:
            Dictionary with connection information
        """
        system_info = self.get_system_info(sid)
        primary_host = self.get_primary_host(sid, host_type)
        
        return {
            'sid': sid,
            'host': primary_host,
            'all_hosts': self.resolve_sid_to_hosts(sid, host_type),
            'ports': system_info.get('ports', {}),
            'client': system_info.get('client'),
            'description': system_info.get('description', '')
        }
    
    def _find_system_by_sid(self, sid: str) -> Optional[Dict[str, Any]]:
        """
        Find system information by SID across all environments.
        
        Args:
            sid: The SAP System ID to find
            
        Returns:
            System information dictionary or None if not found
        """
        for environment in self.landscape_data['landscape'].values():
            if isinstance(environment, dict) and sid in environment:
                return environment[sid]
        return None
    
    def validate_sid(self, sid: str) -> bool:
        """
        Check if a SID exists in the landscape configuration.
        
        Args:
            sid: The SAP System ID to validate
            
        Returns:
            True if SID exists, False otherwise
        """
        return self._find_system_by_sid(sid) is not None
    
    def get_defaults(self) -> Dict[str, Any]:
        """
        Get default configuration values.
        
        Returns:
            Dictionary with default configuration
        """
        return self.landscape_data.get('defaults', {}).copy()
    
    def get_monitoring_config(self) -> Dict[str, Any]:
        """
        Get monitoring configuration values.
        
        Returns:
            Dictionary with monitoring configuration
        """
        return self.landscape_data.get('monitoring', {}).copy()
    
    def get_all_hosts(self, sid: str) -> List[str]:
        """
        Get all hosts for a SID (application servers, database, web dispatcher).
        Convenience method for LLM functions that need all available hosts.
        
        Args:
            sid: The SAP System ID
            
        Returns:
            List of all hostnames for the SID
        """
        system_info = self.get_system_info(sid)
        hosts = system_info.get('hosts', {})
        
        all_hosts = []
        for host_type, host_list in hosts.items():
            if isinstance(host_list, str):
                all_hosts.append(host_list)
            elif isinstance(host_list, list):
                all_hosts.extend(host_list)
        
        return list(set(all_hosts))  # Remove duplicates
    
    def get_app_hosts(self, sid: str) -> List[str]:
        """
        Get application server hosts for a SID.
        Convenience method for LLM functions targeting application servers.
        
        Args:
            sid: The SAP System ID
            
        Returns:
            List of application server hostnames
        """
        return self.resolve_sid_to_hosts(sid, 'application_servers')
    
    def get_hana_hosts(self, sid: str) -> List[str]:
        """
        Get HANA database hosts for a SID.
        Convenience method for LLM functions targeting database servers.
        
        Args:
            sid: The SAP System ID
            
        Returns:
            List of database server hostnames
        """
        return self.resolve_sid_to_hosts(sid, 'database_server')

    def reload_config(self) -> None:
        """Reload the landscape configuration from file."""
        self._load_landscape_config()
        self.logger.info("Landscape configuration reloaded")
