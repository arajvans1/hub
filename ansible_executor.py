"""
Ansible-based command executor for SAP Monitoring Platform
Executes shell and database commands via Ansible without requiring agent deployment
"""
import json
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional
import ansible_runner


class AnsibleExecutor:
    """Executes monitoring commands via Ansible using ansible-runner."""

    def __init__(self, landscape_file: str = "config/landscape.json"):
        """
        Initialize Ansible executor with landscape configuration.

        Args:
            landscape_file: Path to landscape.json configuration file
        """
        self.landscape_file = landscape_file
        self.landscape_data = {}

        # Load landscape configuration
        self._load_landscape_config()

    def _load_landscape_config(self) -> None:
        """Load landscape configuration from JSON file."""
        try:
            landscape_path = Path(self.landscape_file)
            with open(landscape_path, 'r', encoding='utf-8') as file:
                self.landscape_data = json.load(file)
            print(f"Loaded landscape configuration for Ansible from {self.landscape_file}")
        except FileNotFoundError:
            print(f"Warning: Landscape file not found: {self.landscape_file}")
            print("Ansible executor will use fallback configuration")
        except json.JSONDecodeError as e:
            print(f"Warning: Invalid JSON in landscape file: {e}")
            print("Ansible executor will use fallback configuration")

    def _find_sid_for_server(self, hostname: str) -> Optional[str]:
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

    def _is_database_server(self, hostname: str, sid: str) -> bool:
        """
        Check if hostname is a database server for the given SID.

        Args:
            hostname: The hostname to check
            sid: The SID to check against

        Returns:
            True if hostname is a database server, False otherwise
        """
        if sid not in self.landscape_data:
            return False

        system_config = self.landscape_data[sid]
        database = system_config.get('database', {})
        hana_hosts = database.get('hana_hosts', [])

        if isinstance(hana_hosts, list):
            return hostname in hana_hosts
        elif isinstance(hana_hosts, str):
            return hostname == hana_hosts

        return False

    def execute(self, server: str, command: str, backend: str, timeout: int = 30) -> Dict[str, Any]:
        """
        Execute command via Ansible.

        Args:
            server: Target server hostname
            command: Command to execute
            backend: Backend type (shell, database)
            timeout: Execution timeout in seconds

        Returns:
            Dict with execution results or error
        """
        try:
            if backend == "shell":
                return self._execute_shell(server, command, timeout)
            elif backend == "database":
                return self._execute_database(server, command, timeout)
            else:
                return {"error": f"Ansible executor does not support backend: {backend}"}

        except Exception as e:
            return {"error": f"Ansible execution failed: {str(e)}"}

    def _execute_shell(self, server: str, command: str, timeout: int) -> Dict[str, Any]:
        """Execute shell command via Ansible shell module."""

        # Create playbook for shell command execution
        playbook = [
            {
                'name': 'Execute monitoring command',
                'hosts': server,
                'gather_facts': False,
                'tasks': [
                    {
                        'name': 'Run shell command',
                        'ansible.builtin.shell': command,
                        'register': 'command_result',
                        'async': timeout,
                        'poll': 5
                    }
                ]
            }
        ]

        return self._run_playbook(playbook, server, timeout)

    def _execute_database(self, server: str, command: str, timeout: int) -> Dict[str, Any]:
        """
        Execute database query via Ansible.

        For SAP HANA, we use shell module with hdbsql or similar tools.
        Future: Use community.general.hana_query module if available.
        """

        # For now, execute SQL via shell using hdbsql
        # Assumes hdbsql is available and configured on target host
        shell_command = f'echo "{command}" | hdbsql -j -x'

        playbook = [
            {
                'name': 'Execute database query',
                'hosts': server,
                'gather_facts': False,
                'tasks': [
                    {
                        'name': 'Run database query',
                        'ansible.builtin.shell': shell_command,
                        'register': 'query_result',
                        'async': timeout,
                        'poll': 5
                    }
                ]
            }
        ]

        return self._run_playbook(playbook, server, timeout)

    def _run_playbook(self, playbook: list, server: str, timeout: int) -> Dict[str, Any]:
        """
        Execute Ansible playbook and return standardized results.

        Args:
            playbook: Ansible playbook structure
            server: Target server
            timeout: Timeout in seconds

        Returns:
            Standardized result dictionary matching Agent interface
        """
        # Create temporary directory for ansible-runner
        with tempfile.TemporaryDirectory() as tmpdir:
            private_data_dir = Path(tmpdir)

            # Write playbook to temp directory
            playbook_path = private_data_dir / 'project' / 'playbook.yml'
            playbook_path.parent.mkdir(parents=True, exist_ok=True)

            with open(playbook_path, 'w') as f:
                import yaml
                yaml.dump(playbook, f)

            # Create inventory - try file first, fallback to dynamic
            inventory = self._create_inventory(server)

            # Run playbook using ansible-runner
            result = ansible_runner.run(
                private_data_dir=str(private_data_dir),
                playbook='playbook.yml',
                inventory=inventory,
                quiet=True,
                verbosity=0
            )

            return self._parse_ansible_result(result, server)

    def _create_inventory(self, server: str) -> Dict[str, Any]:
        """
        Create dynamic Ansible inventory from landscape.json.

        Args:
            server: Target server hostname

        Returns:
            Inventory dictionary for ansible-runner

        Raises:
            ValueError: If server not found or ssh_config not properly configured
        """
        # Find which SID this server belongs to
        sid = self._find_sid_for_server(server)

        if not sid:
            raise ValueError(
                f"Server '{server}' not found in landscape.json. "
                f"Please add this server to the landscape configuration."
            )

        # Get SSH config from landscape.json
        system_config = self.landscape_data[sid]
        ssh_config = system_config.get('ssh_config')

        if not ssh_config:
            raise ValueError(
                f"No ssh_config found for SID '{sid}' in landscape.json. "
                f"Please add ssh_config section with app_server_user and database_user."
            )

        # Determine user based on server type
        is_db_server = self._is_database_server(server, sid)

        if is_db_server:
            user = ssh_config.get('database_user')
            if not user:
                raise ValueError(
                    f"No database_user defined in ssh_config for SID '{sid}'. "
                    f"Please add database_user to ssh_config section."
                )
        else:
            user = ssh_config.get('app_server_user')
            if not user:
                raise ValueError(
                    f"No app_server_user defined in ssh_config for SID '{sid}'. "
                    f"Please add app_server_user to ssh_config section."
                )

        # Build dynamic inventory
        return {
            'all': {
                'hosts': {
                    server: {
                        'ansible_host': server,
                        'ansible_user': user,
                        'ansible_ssh_common_args': '-o ControlMaster=auto -o ControlPersist=60s -o StrictHostKeyChecking=no',
                        'ansible_timeout': 30,
                        'ansible_python_interpreter': '/usr/bin/python3'
                    }
                }
            }
        }

    def _parse_ansible_result(self, result: ansible_runner.Runner, server: str) -> Dict[str, Any]:
        """
        Parse ansible-runner result into standardized format.

        Args:
            result: ansible-runner result object
            server: Target server name

        Returns:
            Standardized result matching Agent interface
        """
        # Check overall status
        if result.status == 'failed':
            return {
                "error": "Ansible playbook execution failed",
                "details": self._extract_error_details(result),
                "server": server,
                "ansible_status": result.status
            }

        if result.status == 'timeout':
            return {
                "error": "Ansible playbook execution timed out",
                "server": server,
                "ansible_status": result.status
            }

        # Extract task results
        if result.status == 'successful':
            return self._extract_success_results(result, server)

        # Unknown status
        return {
            "error": f"Unknown Ansible status: {result.status}",
            "server": server,
            "ansible_status": result.status
        }

    def _extract_success_results(self, result: ansible_runner.Runner, server: str) -> Dict[str, Any]:
        """Extract successful execution results."""

        # Try to get task results from events
        task_results = []

        for event in result.events:
            if event.get('event') == 'runner_on_ok':
                event_data = event.get('event_data', {})
                task_data = event_data.get('res', {})

                # Extract stdout, stderr, rc
                if 'stdout' in task_data:
                    return {
                        "success": True,
                        "server": server,
                        "stdout": task_data.get('stdout', ''),
                        "stderr": task_data.get('stderr', ''),
                        "rc": task_data.get('rc', 0),
                        "ansible_status": result.status
                    }

        # Fallback if no task output found - this is actually an error!
        return {
            "error": "Could not extract command output from Ansible events",
            "server": server,
            "ansible_status": result.status,
            "details": "Ansible reported success but no task output was found in events"
        }

    def _extract_error_details(self, result: ansible_runner.Runner) -> str:
        """Extract detailed error information from failed run."""

        error_messages = []

        for event in result.events:
            if event.get('event') in ['runner_on_failed', 'runner_on_unreachable']:
                event_data = event.get('event_data', {})
                task_data = event_data.get('res', {})

                # Extract error message
                msg = task_data.get('msg', '')
                stderr = task_data.get('stderr', '')

                if msg:
                    error_messages.append(f"Message: {msg}")
                if stderr:
                    error_messages.append(f"Stderr: {stderr}")

        if error_messages:
            return '; '.join(error_messages)

        return "No detailed error information available"

    def test_connection(self, server: str) -> bool:
        """
        Test SSH connection to server using Ansible ping module.

        Args:
            server: Target server hostname

        Returns:
            True if connection successful, False otherwise
        """
        playbook = [
            {
                'name': 'Test connection',
                'hosts': server,
                'gather_facts': False,
                'tasks': [
                    {
                        'name': 'Ping server',
                        'ansible.builtin.ping': {}
                    }
                ]
            }
        ]

        result = self._run_playbook(playbook, server, timeout=10)
        return result.get('success', False)
