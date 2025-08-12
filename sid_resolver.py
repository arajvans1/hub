"""
SID Resolver for SAP S/4HANA Monitoring System.

Provides the 4 core functions that the LLM will call:
0. get_available_sids - Returns list of all available SIDs
1. get_all_hosts - Returns all hosts (app + DB) for a SID
2. get_app_hosts - Returns only application server hosts  
3. get_hana_hosts - Returns HANA DB nodes
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Union


class SIDResolver:
    """
    SAP System ID resolver with ONLY 4 core functions for LLM function calling.
    
    This is the ONLY place that should contain SID resolution logic.
    """
    
    def __init__(self, landscape_config_path: Union[str, Path]):
        """
        Initialize the SID resolver with landscape configuration.
        
        Args:
            landscape_config_path: Path to the landscape.json configuration file
        """
        self.landscape_config_path = Path(landscape_config_path)
        self.landscape_data: Dict[str, dict] = {}
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
    # THE ONLY 4 FUNCTIONS FOR LLM CALLING
    # =====================================
    
    def get_available_sids(self) -> List[str]:
        """
        Get all available SAP System IDs (SIDs) in the landscape.
        
        This is Function 0 that the LLM will call to discover available systems.
        
        Returns:
            List of available SID names
        """
        return list(self.landscape_data.keys())
    
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
    
    def find_sid_by_host(self, hostname: str) -> Union[str, None]:
        """
        Find which SID a hostname belongs to.
        
        Args:
            hostname: The hostname to search for
            
        Returns:
            SID name if found, None if not found
        """
        for sid, system_config in self.landscape_data.items():
            # Check application servers
            app_servers = system_config.get('app_servers', {})
            for server_type, hosts in app_servers.items():
                if isinstance(hosts, list) and hostname in hosts:
                    return sid
                elif isinstance(hosts, str) and hostname == hosts:
                    return sid
            
            # Check database servers
            database = system_config.get('database', {})
            hana_hosts = database.get('hana_hosts', [])
            if isinstance(hana_hosts, list) and hostname in hana_hosts:
                return sid
            elif isinstance(hana_hosts, str) and hostname == hana_hosts:
                return sid
        
        return None
