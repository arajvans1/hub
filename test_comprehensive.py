#!/usr/bin/env python3
"""
Comprehensive Test Suite for SAP S/4HANA Monitoring Platform

Tests all components:
- SID Resolver
- Function Schema Builder  
- Command Builder
- Vault Manager
- Agent Communication
- Integration Tests
"""

import json
import logging
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

# Import all modules to test
from sid_resolver import SIDResolver
from function_schema_builder import FunctionSchemaBuilder
from command_builder import CommandBuilder
from vault import VaultManager, VaultError
from agent import Agent


class TestSIDResolver(unittest.TestCase):
    """Test the SID Resolver functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_landscape = {
            "PRD": {
                "application_sid": "PRD",
                "description": "Production System",
                "app_servers": {
                    "ascs": ["ascs01.prd.local"],
                    "pas": ["pas01.prd.local"],
                    "aas": ["aas01.prd.local", "aas02.prd.local"]
                },
                "database": {
                    "hana_sid": "H01",
                    "tenant_db": "PRD",
                    "hana_hosts": ["hana01.prd.local", "hana02.prd.local"]
                }
            },
            "QAS": {
                "application_sid": "QAS",
                "description": "Quality System",
                "app_servers": {
                    "ascs": ["ascs01.qas.local"],
                    "pas": ["pas01.qas.local"],
                    "aas": []
                },
                "database": {
                    "hana_sid": "H02",
                    "tenant_db": "QAS",
                    "hana_hosts": ["hana01.qas.local"]
                }
            }
        }
        
        # Create temporary landscape file
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        json.dump(self.test_landscape, self.temp_file)
        self.temp_file.close()
        
        self.resolver = SIDResolver(self.temp_file.name)
    
    def tearDown(self):
        """Clean up test fixtures."""
        os.unlink(self.temp_file.name)
    
    def test_get_available_sids(self):
        """Test getting available SIDs."""
        sids = self.resolver.get_available_sids()
        self.assertEqual(set(sids), {"PRD", "QAS"})
        self.assertIsInstance(sids, list)
    
    def test_get_all_hosts_prd(self):
        """Test getting all hosts for PRD system."""
        hosts = self.resolver.get_all_hosts("PRD")
        expected_hosts = {
            "ascs01.prd.local", "pas01.prd.local", 
            "aas01.prd.local", "aas02.prd.local",
            "hana01.prd.local", "hana02.prd.local"
        }
        self.assertEqual(set(hosts), expected_hosts)
    
    def test_get_all_hosts_qas(self):
        """Test getting all hosts for QAS system."""
        hosts = self.resolver.get_all_hosts("QAS")
        expected_hosts = {
            "ascs01.qas.local", "pas01.qas.local",
            "hana01.qas.local"
        }
        self.assertEqual(set(hosts), expected_hosts)
    
    def test_get_app_hosts(self):
        """Test getting application hosts only."""
        app_hosts = self.resolver.get_app_hosts("PRD")
        expected_app_hosts = {
            "ascs01.prd.local", "pas01.prd.local",
            "aas01.prd.local", "aas02.prd.local"
        }
        self.assertEqual(set(app_hosts), expected_app_hosts)
    
    def test_get_hana_hosts(self):
        """Test getting HANA hosts only."""
        hana_hosts = self.resolver.get_hana_hosts("PRD")
        expected_hana_hosts = ["hana01.prd.local", "hana02.prd.local"]
        self.assertEqual(hana_hosts, expected_hana_hosts)
    
    def test_sid_not_found(self):
        """Test handling of non-existent SID."""
        with self.assertRaises(ValueError) as context:
            self.resolver.get_all_hosts("INVALID")
        self.assertIn("SID 'INVALID' not found", str(context.exception))
    
    def test_invalid_landscape_file(self):
        """Test handling of invalid landscape file."""
        with self.assertRaises(FileNotFoundError):
            SIDResolver("/nonexistent/file.json")
    
    def test_invalid_json_format(self):
        """Test handling of invalid JSON in landscape file."""
        bad_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        bad_file.write("{ invalid json }")
        bad_file.close()
        
        try:
            with self.assertRaises(ValueError):
                SIDResolver(bad_file.name)
        finally:
            os.unlink(bad_file.name)


class TestFunctionSchemaBuilder(unittest.TestCase):
    """Test the Function Schema Builder."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.command_specs = {
            "get_system_status": {
                "description": "Get overall system status",
                "agent_command": "systemctl status sap{{.sid}}",
                "required": ["sid"],
                "params": {
                    "timeout": "30"
                }
            },
            "get_process_list": {
                "description": "Get SAP process list",
                "agent_command": "ps aux | grep {{.sid}}",
                "required": ["sid", "server"],
                "params": {}
            }
        }
        self.builder = FunctionSchemaBuilder(self.command_specs)
    
    def test_build_function_schemas(self):
        """Test building OpenAI function schemas."""
        schemas = self.builder.build_function_schemas()
        
        self.assertEqual(len(schemas), 2)
        
        # Test first schema
        schema1 = schemas[0]
        self.assertEqual(schema1["type"], "function")
        self.assertEqual(schema1["function"]["name"], "get_system_status")
        self.assertIn("description", schema1["function"])
        self.assertEqual(schema1["function"]["parameters"]["type"], "object")
        self.assertIn("sid", schema1["function"]["parameters"]["properties"])
        self.assertEqual(schema1["function"]["parameters"]["required"], ["sid"])
    
    def test_required_parameters(self):
        """Test that required parameters are properly handled."""
        schemas = self.builder.build_function_schemas()
        
        # Find the schema with both sid and server required
        process_schema = next(s for s in schemas if s["function"]["name"] == "get_process_list")
        
        self.assertEqual(set(process_schema["function"]["parameters"]["required"]), {"sid", "server"})
        self.assertIn("sid", process_schema["function"]["parameters"]["properties"])
        self.assertIn("server", process_schema["function"]["parameters"]["properties"])
    
    def test_optional_parameters(self):
        """Test that optional parameters are included."""
        schemas = self.builder.build_function_schemas()
        
        # Find the schema with timeout parameter
        status_schema = next(s for s in schemas if s["function"]["name"] == "get_system_status")
        
        self.assertIn("timeout", status_schema["function"]["parameters"]["properties"])
        # Timeout should not be in required
        self.assertNotIn("timeout", status_schema["function"]["parameters"]["required"])


class TestCommandBuilder(unittest.TestCase):
    """Test the Command Builder."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.command_specs = {
            "get_system_status": {
                "description": "Get overall system status",
                "agent_command": "systemctl status sap{{.sid}}",
                "required": ["sid"],
                "params": {
                    "timeout": "30"
                }
            },
            "get_memory_usage": {
                "description": "Get memory usage for server",
                "agent_command": "ssh {{.server}} 'free -h'",
                "required": ["server"],
                "params": {}
            }
        }
        self.builder = CommandBuilder(self.command_specs)
    
    def test_build_command_simple(self):
        """Test building a simple command."""
        spec = self.command_specs["get_system_status"]
        params = {"sid": "PRD"}
        
        command = self.builder.build_command(spec, params)
        self.assertEqual(command, "systemctl status sapPRD")
    
    def test_build_command_multiple_params(self):
        """Test building command with multiple parameters."""
        spec = self.command_specs["get_memory_usage"]
        params = {"server": "app01.prd.local"}
        
        command = self.builder.build_command(spec, params)
        self.assertEqual(command, "ssh app01.prd.local 'free -h'")
    
    def test_validate_command_valid(self):
        """Test command validation with valid parameters."""
        params = {"sid": "PRD"}
        result = self.builder.validate_command("get_system_status", params)
        self.assertTrue(result)
    
    def test_validate_command_missing_required(self):
        """Test command validation with missing required parameters."""
        params = {}  # Missing required 'sid'
        result = self.builder.validate_command("get_system_status", params)
        self.assertFalse(result)
    
    def test_validate_command_extra_params(self):
        """Test command validation with extra parameters (should pass)."""
        params = {"sid": "PRD", "extra_param": "value"}
        result = self.builder.validate_command("get_system_status", params)
        self.assertTrue(result)
    
    def test_validate_command_nonexistent(self):
        """Test validation of non-existent command."""
        params = {"sid": "PRD"}
        result = self.builder.validate_command("nonexistent_command", params)
        self.assertFalse(result)


class TestVaultManager(unittest.TestCase):
    """Test the Vault Manager."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_vault_data = {
            "azure_openai_api_key": "test-api-key-12345",
            "azure_openai_endpoint": "https://test.openai.azure.com/",
            "monitoring_user": "mon_user",
            "monitoring_password": "secret123"
        }
        
        # Create temporary vault file
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        json.dump(self.test_vault_data, self.temp_file)
        self.temp_file.close()
    
    def tearDown(self):
        """Clean up test fixtures."""
        os.unlink(self.temp_file.name)
    
    def test_load_vault_success(self):
        """Test successful vault loading."""
        vault = VaultManager(self.temp_file.name)
        self.assertEqual(len(vault.vault_data), 4)
        self.assertIn("azure_openai_api_key", vault.vault_data)
    
    def test_get_secret_success(self):
        """Test getting an existing secret."""
        vault = VaultManager(self.temp_file.name)
        api_key = vault.get_secret("azure_openai_api_key")
        self.assertEqual(api_key, "test-api-key-12345")
    
    def test_get_secret_not_found(self):
        """Test getting a non-existent secret."""
        vault = VaultManager(self.temp_file.name)
        with self.assertRaises(VaultError) as context:
            vault.get_secret("nonexistent_key")
        self.assertIn("Secret 'nonexistent_key' not found", str(context.exception))
    
    def test_get_azure_openai_config(self):
        """Test getting Azure OpenAI configuration."""
        vault = VaultManager(self.temp_file.name)
        config = vault.get_azure_openai_config()
        
        self.assertIn("api_key", config)
        self.assertIn("azure_endpoint", config)
        self.assertEqual(config["api_key"], "test-api-key-12345")
        self.assertEqual(config["azure_endpoint"], "https://test.openai.azure.com/")
    
    def test_list_secrets(self):
        """Test listing all secret keys."""
        vault = VaultManager(self.temp_file.name)
        secrets = vault.list_secrets()
        
        expected_keys = {
            "azure_openai_api_key", "azure_openai_endpoint",
            "monitoring_user", "monitoring_password"
        }
        self.assertEqual(set(secrets), expected_keys)
    
    def test_vault_file_not_found(self):
        """Test handling when vault file doesn't exist."""
        vault = VaultManager("/nonexistent/vault.json")
        self.assertEqual(vault.vault_data, {})


class TestAgent(unittest.TestCase):
    """Test the Agent communication."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.agent = Agent("monitoring.local")
    
    @patch('agent.requests.post')
    def test_call_agent_api_success(self, mock_post):
        """Test successful agent API call."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {"cpu_usage": "15%", "memory_usage": "60%"}
        }
        mock_post.return_value = mock_response
        
        result = self.agent.call_agent_api("app01", "systemctl status sapprd", "shell")
        
        self.assertIn("status", result)
        self.assertEqual(result["status"], "success")
        self.assertIn("data", result)
    
    @patch('agent.requests.post')
    def test_call_agent_api_http_error(self, mock_post):
        """Test agent API call with HTTP error."""
        # Mock HTTP error response
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.reason = "Not Found"
        mock_response.text = "Agent not found"
        mock_post.return_value = mock_response
        
        result = self.agent.call_agent_api("app01", "test command", "shell")
        
        self.assertIn("error", result)
        self.assertIn("HTTP 404", result["error"])
    
    @patch('agent.requests.post')
    def test_call_agent_api_json_error(self, mock_post):
        """Test agent API call with invalid JSON response."""
        # Mock response with invalid JSON
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_response.text = "Invalid response"
        mock_post.return_value = mock_response
        
        result = self.agent.call_agent_api("app01", "test command", "shell")
        
        self.assertIn("error", result)
        self.assertIn("Invalid JSON response", result["error"])
    
    @patch('agent.requests.post')
    def test_call_agent_api_network_error(self, mock_post):
        """Test agent API call with network error."""
        # Mock network error
        mock_post.side_effect = Exception("Connection timeout")
        
        result = self.agent.call_agent_api("app01", "test command", "shell")
        
        self.assertIn("error", result)
        self.assertIn("Unexpected error", result["error"])
    
    def test_discover_agent(self):
        """Test agent discovery functionality."""
        agent_url = self.agent.discover_agent("app01")
        expected_url = "http://app01.monitoring.local:8090"
        self.assertEqual(agent_url, expected_url)


class TestIntegration(unittest.TestCase):
    """Integration tests for the complete system."""
    
    def setUp(self):
        """Set up integration test fixtures."""
        # Create test landscape
        self.test_landscape = {
            "PRD": {
                "application_sid": "PRD",
                "app_servers": {
                    "pas": ["app01.prd.local"],
                    "aas": ["app02.prd.local"]
                },
                "database": {
                    "hana_hosts": ["db01.prd.local"]
                }
            }
        }
        
        # Create temporary files
        self.landscape_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        json.dump(self.test_landscape, self.landscape_file)
        self.landscape_file.close()
        
        self.vault_data = {
            "azure_openai_api_key": "test-key",
            "azure_openai_endpoint": "https://test.openai.azure.com/"
        }
        
        self.vault_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        json.dump(self.vault_data, self.vault_file)
        self.vault_file.close()
        
        # Command specs
        self.command_specs = {
            "get_system_status": {
                "description": "Get system status",
                "agent_command": "systemctl status sap{{.sid}}",
                "required": ["sid"],
                "params": {}
            }
        }
        
        # Initialize components
        self.resolver = SIDResolver(self.landscape_file.name)
        self.vault = VaultManager(self.vault_file.name)
        self.schema_builder = FunctionSchemaBuilder(self.command_specs)
        self.command_builder = CommandBuilder(self.command_specs)
        self.agent = Agent("monitoring.local")
    
    def tearDown(self):
        """Clean up integration test fixtures."""
        os.unlink(self.landscape_file.name)
        os.unlink(self.vault_file.name)
    
    def test_full_workflow_sid_to_hosts_to_commands(self):
        """Test complete workflow from SID resolution to command building."""
        # 1. Get available SIDs
        sids = self.resolver.get_available_sids()
        self.assertIn("PRD", sids)
        
        # 2. Get hosts for a SID
        app_hosts = self.resolver.get_app_hosts("PRD")
        self.assertIn("app01.prd.local", app_hosts)
        
        # 3. Build function schemas
        schemas = self.schema_builder.build_function_schemas()
        self.assertEqual(len(schemas), 1)
        
        # 4. Validate and build command
        params = {"sid": "PRD"}
        is_valid = self.command_builder.validate_command("get_system_status", params)
        self.assertTrue(is_valid)
        
        spec = self.command_specs["get_system_status"]
        command = self.command_builder.build_command(spec, params)
        self.assertEqual(command, "systemctl status sapPRD")
    
    def test_vault_integration_with_azure_config(self):
        """Test vault integration for Azure OpenAI configuration."""
        config = self.vault.get_azure_openai_config()
        
        self.assertIn("api_key", config)
        self.assertIn("azure_endpoint", config)
        self.assertEqual(config["api_key"], "test-key")
    
    def test_error_handling_chain(self):
        """Test error handling across components."""
        # Test SID not found
        with self.assertRaises(ValueError):
            self.resolver.get_all_hosts("INVALID")
        
        # Test invalid command
        result = self.command_builder.validate_command("invalid_command", {})
        self.assertFalse(result)
        
        # Test missing vault secret
        with self.assertRaises(VaultError):
            self.vault.get_secret("nonexistent_secret")


class TestPerformance(unittest.TestCase):
    """Performance tests for the system."""
    
    def test_sid_resolver_performance(self):
        """Test SID resolver performance with large landscape."""
        # Create large test landscape
        large_landscape = {}
        for i in range(100):
            sid = f"SID{i:03d}"
            large_landscape[sid] = {
                "app_servers": {
                    "pas": [f"app{j:02d}.{sid.lower()}.local" for j in range(5)],
                    "aas": [f"aas{j:02d}.{sid.lower()}.local" for j in range(10)]
                },
                "database": {
                    "hana_hosts": [f"db{j:02d}.{sid.lower()}.local" for j in range(2)]
                }
            }
        
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        json.dump(large_landscape, temp_file)
        temp_file.close()
        
        try:
            # Test performance
            import time
            start_time = time.time()
            
            resolver = SIDResolver(temp_file.name)
            sids = resolver.get_available_sids()
            
            # Test getting hosts for multiple SIDs
            for sid in sids[:10]:  # Test first 10 SIDs
                all_hosts = resolver.get_all_hosts(sid)
                app_hosts = resolver.get_app_hosts(sid)
                hana_hosts = resolver.get_hana_hosts(sid)
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            # Should complete within reasonable time (adjust threshold as needed)
            self.assertLess(execution_time, 5.0, "Performance test took too long")
            
        finally:
            os.unlink(temp_file.name)


def run_comprehensive_tests():
    """Run all comprehensive tests with detailed reporting."""
    print("=" * 80)
    print("🔍 SAP S/4HANA Monitoring Platform - Comprehensive Test Suite")
    print("=" * 80)
    
    # Configure logging for tests
    logging.basicConfig(level=logging.WARNING)
    
    # Create test suite
    test_classes = [
        TestSIDResolver,
        TestFunctionSchemaBuilder,
        TestCommandBuilder,
        TestVaultManager,
        TestAgent,
        TestIntegration,
        TestPerformance
    ]
    
    total_tests = 0
    total_failures = 0
    total_errors = 0
    
    for test_class in test_classes:
        print(f"\n📋 Running {test_class.__name__}...")
        suite = unittest.TestLoader().loadTestsFromTestCase(test_class)
        runner = unittest.TextTestRunner(verbosity=2, stream=open(os.devnull, 'w'))
        result = runner.run(suite)
        
        tests_run = result.testsRun
        failures = len(result.failures)
        errors = len(result.errors)
        
        total_tests += tests_run
        total_failures += failures
        total_errors += errors
        
        # Print results for this test class
        if failures == 0 and errors == 0:
            print(f"   ✅ {tests_run} tests passed")
        else:
            print(f"   ❌ {failures} failures, {errors} errors out of {tests_run} tests")
            
            # Print failure details
            for failure in result.failures:
                print(f"      FAIL: {failure[0]}")
                print(f"            {failure[1].split('AssertionError:')[-1].strip()}")
            
            for error in result.errors:
                print(f"      ERROR: {error[0]}")
                print(f"             {error[1].split('Exception:')[-1].strip()}")
    
    # Final summary
    print("\n" + "=" * 80)
    print("📊 TEST SUMMARY")
    print("=" * 80)
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {total_tests - total_failures - total_errors}")
    print(f"Failed: {total_failures}")
    print(f"Errors: {total_errors}")
    
    if total_failures == 0 and total_errors == 0:
        print("\n🎉 ALL TESTS PASSED! System is ready for deployment.")
        return True
    else:
        print(f"\n⚠️  {total_failures + total_errors} test(s) failed. Please fix issues before deployment.")
        return False


if __name__ == "__main__":
    success = run_comprehensive_tests()
    exit(0 if success else 1)
