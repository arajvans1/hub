# HANA Database Authentication Setup

This guide explains how to set up authentication for HANA database queries executed via Ansible's `community.sap_libs.sap_hdbsql` module.

## Overview

The `ansible_executor.py` uses the `community.sap_libs.sap_hdbsql` module to execute SQL queries against SAP HANA databases. This module requires proper authentication configuration.

## Prerequisites

1. **Install community.sap_libs collection:**
```bash
ansible-galaxy collection install community.sap_libs
```

2. **Verify installation:**
```bash
ansible-galaxy collection list | grep sap_libs
```

## Authentication Methods

The `community.sap_libs.sap_hdbsql` module supports two authentication methods:

### Method 1: hdbuserstore (Recommended)

**Most secure method** - credentials stored in encrypted hdbuserstore on the HANA server.

#### Setup on HANA Server:

```bash
# SSH to HANA server as database user (e.g., h01adm)
ssh h01adm@hana01.prd.local

# Create hdbuserstore key
hdbuserstore SET <KEYNAME> <HOST>:<PORT> <USERNAME> <PASSWORD>

# Example:
hdbuserstore SET H01KEY hana01.prd.local:30013 SYSTEM YourPassword123

# Verify key creation
hdbuserstore LIST
```

#### Configuration in landscape.json:

The userkey is automatically generated from `hana_sid`: `{hana_sid}KEY`

```json
"database": {
  "hana_sid": "H01",
  "tenant_db": "PRD",
  "instance": "00"
}
```

This will use userkey: `H01KEY`

#### Test manually:

```bash
# Test connection with userkey
hdbsql -U H01KEY "SELECT * FROM DUMMY"
```

### Method 2: User/Password (Fallback)

**Less secure** - requires storing credentials in Ansible vault or host variables.

#### Update ansible_executor.py:

Modify `_execute_database()` method to use user/password instead of userkey:

```python
'community.sap_libs.sap_hdbsql': {
    'sid': hana_sid.upper(),
    'instance': instance,
    'database': tenant_db,
    'query': command,
    # Use user/password authentication
    'user': '{{ hana_user }}',
    'password': '{{ hana_password }}'
}
```

#### Store credentials in Ansible Vault:

```bash
# Create vault file
ansible-vault create config/vault.yml

# Add credentials:
---
hana_user: SYSTEM
hana_password: YourPassword123
```

#### Update inventory to use vault:

```ini
[prd_database_servers:vars]
ansible_vault_password_file=config/.vault_pass
```

## Configuration per SID

Update `landscape.json` to include database instance numbers:

```json
{
  "PRD": {
    "database": {
      "hana_sid": "H01",        # HANA system ID
      "tenant_db": "PRD",       # Tenant database name
      "instance": "00",         # HANA instance number (usually 00)
      "hana_hosts": ["hana01.prd.local", "hana02.prd.local"]
    }
  }
}
```

### Finding Instance Number:

On HANA server:
```bash
# As sidadm user
ps -ef | grep hdb | grep sapstart

# Or check /usr/sap/<SID>/HDB<instance>
ls /usr/sap/H01/HDB00  # Instance 00
ls /usr/sap/H01/HDB10  # Instance 10
```

### Finding Tenant Database:

```bash
# Connect to SYSTEMDB
hdbsql -i 00 -n localhost:30013 -u SYSTEM

# List tenant databases
SELECT DATABASE_NAME FROM M_DATABASES WHERE ACTIVE_STATUS = 'YES';
```

## Port Calculation

HANA uses ports based on instance number:
- **SQL port**: `3<instance>13` (e.g., instance 00 = port 30013)
- **SYSTEMDB**: `3<instance>13`
- **Tenant DB**: `3<instance>15`

The `sap_hdbsql` module automatically calculates ports from instance number.

## Testing the Setup

### 1. Test hdbuserstore key:

```bash
# SSH to HANA server
ssh h01adm@hana01.prd.local

# Test key
hdbsql -U H01KEY "SELECT DATABASE_NAME FROM M_DATABASES"
```

### 2. Test via Ansible ad-hoc command:

```bash
ansible hana01.prd.local -m community.sap_libs.sap_hdbsql -a "
  sid=H01
  instance=00
  database=PRD
  userkey=H01KEY
  query='SELECT DATABASE_NAME FROM M_DATABASES'
"
```

### 3. Test via Python (mock LLM):

Update `test_ansible_mock_llm.py` to include database test:

```python
# Test database query
mock_agent.execute_command(
    function_name="check_database_status",
    arguments={"server": "hana01.prd.local"}
)
```

## Troubleshooting

### Error: "authentication failed"
- Verify hdbuserstore key exists: `hdbuserstore LIST`
- Check HANA is listening: `netstat -tlnp | grep 30013`
- Verify tenant database is active: `SELECT * FROM M_DATABASES`

### Error: "module not found: community.sap_libs.sap_hdbsql"
- Install collection: `ansible-galaxy collection install community.sap_libs`
- Verify: `ansible-galaxy collection list | grep sap_libs`

### Error: "connection refused"
- Check firewall rules between Ansible control node and HANA server
- Verify HANA instance is running: `ps -ef | grep hdb`
- Check port: `telnet hana01.prd.local 30013`

### Error: "Invalid instance number"
- Verify instance in landscape.json matches actual HANA instance
- Check: `ls /usr/sap/H01/HDB<instance>`

## Security Best Practices

1. **Always use hdbuserstore** instead of user/password in production
2. **Encrypt Ansible vault** if you must use user/password method
3. **Use read-only database users** for monitoring queries
4. **Rotate credentials regularly** and update hdbuserstore keys
5. **Audit database access** - monitor who executes which queries
6. **Use SSH key authentication** for Ansible connections (already configured)

## Example: Creating Monitoring User

Instead of using SYSTEM, create a dedicated monitoring user:

```sql
-- Connect as SYSTEM
CREATE USER MONITORING_USER PASSWORD YourPassword123;

-- Grant read-only permissions
GRANT SELECT ON SCHEMA _SYS_STATISTICS TO MONITORING_USER;
GRANT SELECT ON SCHEMA SYS TO MONITORING_USER;
GRANT MONITORING TO MONITORING_USER;

-- Create hdbuserstore key
-- (Run on HANA server as h01adm)
hdbuserstore SET H01KEY hana01.prd.local:30013 MONITORING_USER YourPassword123
```

## Next Steps

1. Install community.sap_libs collection on Ansible control node
2. Create hdbuserstore keys on all HANA servers
3. Update landscape.json with correct instance numbers
4. Test connection using Ansible ad-hoc command
5. Run test_ansible_mock_llm.py with database commands
6. Monitor Ansible logs for any authentication errors

## References

- Ansible SAP HANA Module: https://docs.ansible.com/ansible/latest/collections/community/sap_libs/sap_hdbsql_module.html
- SAP HANA hdbuserstore: https://help.sap.com/docs/SAP_HANA_PLATFORM/b3ee5778bc2e4a089d3299b82ec762a7/dd95ac9dbb571014a7d7f0234d762fdb.html
- SAP HANA Security Guide: https://help.sap.com/docs/SAP_HANA_PLATFORM/b3ee5778bc2e4a089d3299b82ec762a7/1e258a707fbb101481ff81c0ab0ad57b.html
