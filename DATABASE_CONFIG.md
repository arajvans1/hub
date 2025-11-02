# Database Configuration Guide

## Overview

The Ansible executor now uses **direct username/password authentication** instead of hdbuserstore keys for HANA database connections.

## Configuration Format

Update your `config/landscape.json` to include database credentials:

```json
{
  "LOCAL": {
    "application_sid": "LOCAL",
    "app_servers": {
      "pas": ["localhost"]
    },
    "database": {
      "hana_sid": "LOC",
      "system_db": "SYSTEMDB",
      "tenant_db": "LOCAL",
      "instance": "00",
      "hana_hosts": [],
      "credentials": {
        "user": "SYSTEM",
        "password": "your_actual_password"
      }
    },
    "ssh_config": {
      "app_server_user": "your_username",
      "database_user": "your_username"
    }
  }
}
```

## Configuration Fields

### database.hana_sid
- **Type**: String (3 characters)
- **Description**: HANA System ID
- **Example**: `"LOC"`, `"H01"`, `"H02"`

### database.system_db
- **Type**: String
- **Description**: HANA System Database name (usually "SYSTEMDB")
- **Default**: If not specified, falls back to tenant_db
- **Example**: `"SYSTEMDB"`

### database.tenant_db
- **Type**: String
- **Description**: HANA Tenant Database name
- **Example**: `"PRD"`, `"QAS"`, `"DEV"`, `"LOCAL"`
- **Note**: Used if system_db is not specified

### database.instance
- **Type**: String (2 digits)
- **Description**: HANA instance number
- **Default**: `"00"`
- **Example**: `"00"`, `"10"`, `"20"`

### database.credentials.user
- **Type**: String
- **Description**: Database username
- **Default**: `"SYSTEM"` if not specified
- **Example**: `"SYSTEM"`, `"MONITORING_USER"`

### database.credentials.password
- **Type**: String
- **Description**: Database password
- **Required**: Yes
- **Security**: Will be used in Ansible playbooks (not exposed in logs)

## How It Works

### Database Selection Logic

The `ansible_executor.py` uses this logic:

```python
# Prioritize system_db, fall back to tenant_db
database_name = config.get('system_db') or config.get('tenant_db')
```

**Use Cases:**
- **Monitoring queries**: Usually run against `SYSTEMDB` → set `system_db`
- **Application queries**: Run against tenant DB → set `tenant_db`
- **Both**: Set both fields, `system_db` takes priority

### Authentication Flow

1. User requests database query (e.g., "check database status")
2. `tool_executor.py` routes to `ansible_executor._execute_database()`
3. Executor loads credentials from landscape.json
4. Ansible playbook created with:
   - `sid`: HANA SID (e.g., "LOC")
   - `instance`: Instance number (e.g., "00")
   - `database`: Database name (from system_db or tenant_db)
   - `user`: Database username
   - `password`: Database password
   - `encrypted`: True (SSL enabled)
   - `validate_certificate`: False (for self-signed certs)
5. Ansible SSH's to HANA server
6. Executes `hdbsql` with credentials
7. Returns query results

## Example Configurations

### Production System (PRD)
```json
"PRD": {
  "database": {
    "hana_sid": "H01",
    "system_db": "SYSTEMDB",
    "tenant_db": "PRD",
    "instance": "00",
    "hana_hosts": ["hana01.prd.local", "hana02.prd.local"],
    "credentials": {
      "user": "MONITORING_USER",
      "password": "SecurePassword123"
    }
  }
}
```

### Local Test System
```json
"LOCAL": {
  "database": {
    "hana_sid": "LOC",
    "system_db": "SYSTEMDB",
    "tenant_db": "LOCAL",
    "instance": "00",
    "hana_hosts": [],
    "credentials": {
      "user": "SYSTEM",
      "password": "LocalTestPassword"
    }
  }
}
```

### Development System (Only Tenant DB)
```json
"DEV": {
  "database": {
    "hana_sid": "H03",
    "tenant_db": "DEV",
    "instance": "00",
    "hana_hosts": ["hana01.dev.local"],
    "credentials": {
      "user": "DEVUSER",
      "password": "DevPassword"
    }
  }
}
```

## Security Considerations

### Current Setup (Development)
- ✅ Passwords stored in landscape.json
- ✅ SSL encryption enabled (`encrypted: True`)
- ✅ Certificate validation disabled (`validate_certificate: False`)
- ⚠️ landscape.json should be in .gitignore
- ⚠️ Suitable for development/testing

### Production Recommendations
1. **Use Ansible Vault** to encrypt landscape.json:
   ```bash
   ansible-vault encrypt config/landscape.json
   ```

2. **Store credentials in vault.py**:
   - Extend `vault.py` to retrieve HANA credentials
   - Remove credentials from landscape.json
   - Update ansible_executor.py to get credentials from vault

3. **Use SSL certificate validation**:
   - Install proper SSL certificates on HANA servers
   - Change `validate_certificate: True`

4. **Use dedicated monitoring user**:
   ```sql
   CREATE USER MONITORING_USER PASSWORD SecurePass123;
   GRANT SELECT ON SCHEMA _SYS_STATISTICS TO MONITORING_USER;
   GRANT MONITORING TO MONITORING_USER;
   ```

## Testing

### 1. Update landscape.json
Replace `YOUR_PASSWORD_HERE` with your actual HANA password.

### 2. Test with Mock LLM
```bash
python test_ansible_mock_llm.py
```

### 3. Expected Output
```
TEST: Database Query
🤖 Mock LLM calling: check_database_status({"server": "localhost"})

📊 Result:
{
  "success": true,
  "stdout": "DATABASE_NAME,ACTIVE_STATUS\nSYSTEMDB,YES\n",
  "rc": 0
}
```

### 4. Verify SSL Connection
The Ansible module automatically handles SSL with the parameters:
- `encrypted: True` → Enables SSL/TLS
- `validate_certificate: False` → Accepts self-signed certificates

## Troubleshooting

### Error: "Missing database credentials"
**Cause**: No `credentials.password` in landscape.json

**Fix**: Add credentials section:
```json
"credentials": {
  "user": "SYSTEM",
  "password": "YourPassword"
}
```

### Error: "Authentication failed"
**Cause**: Wrong username or password

**Fix**: Verify credentials by testing manually:
```bash
hdbsql -n localhost:30013 -d SYSTEMDB -u SYSTEM -p YourPassword "SELECT 1 FROM DUMMY"
```

### Error: "Cannot connect to database"
**Cause**: Wrong instance number or HANA not running

**Fix**: Check instance number:
```bash
ps -ef | grep hdb
# Look for HDB<instance> in path
```

### Error: "Module not found: community.sap_libs.sap_hdbsql"
**Cause**: Ansible collection not installed

**Fix**:
```bash
ansible-galaxy collection install community.sap_libs
```

## Migration from hdbuserstore

If you were previously using hdbuserstore keys:

**Old approach (not used anymore):**
```python
'userkey': 'H01KEY'  # Required hdbuserstore key on HANA server
```

**New approach (current):**
```python
'user': db_user,      # From landscape.json
'password': db_password,  # From landscape.json
'encrypted': True,
'validate_certificate': False
```

**Benefits:**
- ✅ No hdbuserstore setup required on HANA servers
- ✅ Credentials managed centrally in landscape.json
- ✅ Easier testing and development
- ✅ SSL handled automatically by Ansible module

## Next Steps

1. ✅ Update landscape.json with actual passwords
2. ✅ Test with `test_ansible_mock_llm.py`
3. ⚠️ Add landscape.json to .gitignore (if not already)
4. 📋 Plan migration to vault for production
5. 📋 Consider dedicated monitoring database user
