# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI-powered conversational monitoring platform for SAP S/4HANA systems using Azure OpenAI's GPT-4 with function calling. Converts natural language queries like "Check CPU usage on server01" into structured monitoring commands executed against SAP systems.

## Common Development Commands

### Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Configure Azure OpenAI credentials (required for first run)
# Edit config/vault.json with your credentials:
{
  "azure_openai_api_key": "your-api-key",
  "azure_openai_endpoint": "https://your-resource.openai.azure.com/"
}
```

### Running the Application
```bash
# CLI mode (interactive chat)
python llm.py

# Web server mode (FastAPI)
python fastapi_server.py
# Then access http://localhost:8000
```

### Testing
```bash
# Quick system validation
python -c "
from llm import SharedResources
shared = SharedResources()
shared.initialize()
print(f'✅ {len(shared.commands_loader.get_commands())} commands loaded')
print(f'✅ {len(shared.sid_resolver.get_available_sids())} SIDs available')
print(f'✅ {len(shared.tools)} Azure OpenAI schemas generated')
print('🚀 System ready!')
"

# Run test suite
python test_comprehensive.py
python test_host_validation.py
```

## Architecture & Data Flow

### Hybrid Execution Model

This project uses a **hybrid execution architecture** combining Ansible (for simple commands) and Go agents (for complex protocols):

1. **LLM Chatbot Backend** (This Repository)
   - Natural language interface using Azure OpenAI
   - Configuration-driven command management (YAML)
   - SAP landscape management and host resolution
   - No singletons - uses `SharedResources` container for dependency injection
   - **Hybrid executor routing** based on backend configuration

2. **Ansible Executor** (New in this branch)
   - Executes shell and database commands via SSH
   - No agent deployment required
   - Uses `ansible-runner` for Python integration
   - SSH connection pooling for performance

3. **Go Monitoring Agent** (External Component - Optional)
   - Used only for SOAP/REST calls and streaming data
   - Receives HTTP requests from this Python backend
   - Endpoint pattern: `http://{server}.{domain}:8090/execute`

### Request Flow
```
User Input → FastAPI /chat
    ↓
SAPMonitoringAgent.chat()
    ↓
Azure OpenAI (GPT-4) Function Calling
    ↓
ToolExecutor routes to:
    ├─ SIDResolver (4 functions: get_available_sids, get_all_hosts, get_app_hosts, get_hana_hosts)
    └─ CommandBuilder → Executor routing:
                         ├─ ansible.shell → AnsibleExecutor → SSH → Execute
                         ├─ ansible.database → AnsibleExecutor → SSH → Execute
                         └─ agent.soap → Agent.call_agent_api() → Go Agent → Execute
    ↓
LLM interprets response → User
```

### Core Components

- **`SharedResources`** (llm.py) - Central dependency container initialized once at startup
- **`SAPMonitoringAgent`** (llm.py) - Main orchestrator managing Azure OpenAI client, chat history, and multi-step reasoning (max 3 steps)
- **`SIDResolver`** (sid_resolver.py) - SAP System ID discovery from config/landscape.json (4 SIDs: PRD, QAS, DEV, SBX)
- **`CommandLoader`** (command_loader.py) - Loads commands from config/commands.yaml (supports inline and file-based commands)
- **`CommandBuilder`** (command_builder.py) - Builds executable commands with parameter substitution ({{.param}} templating)
- **`FunctionSchemaBuilder`** (function_schema_builder.py) - Generates Azure OpenAI-compatible function schemas
- **`ToolExecutor`** (tool_executor.py) - Routes function calls to appropriate executor, validates host types (app vs database), parallel execution via ThreadPoolExecutor
- **`AnsibleExecutor`** (ansible_executor.py) - Executes shell/database commands via Ansible (no agent deployment)
- **`Agent`** (agent.py) - HTTP client for Go monitoring agent communication (SOAP/REST only)
- **`VaultManager`** (vault.py) - Dev: file-based credentials; Prod: enterprise vault stubs (Azure Key Vault, HashiCorp, AWS Secrets Manager)

## Configuration Files

### config/commands.yaml
Defines all monitoring commands with YAML structure:
- **SID Resolution Functions** (4): get_available_sids, get_all_hosts, get_app_hosts, get_hana_hosts
- **Monitoring Commands** (11): cpu_info, memory_info, disk_usage, get_process_list, check_database_status, check_sap_services, hana_system_overview, hana_process_status, hana_service_status, sap_performance_analysis, user_session_analysis

Each command specifies:
- `description`: Function purpose for LLM
- `params`: Default parameter values
- `required`: Array of required parameters
- `allowed_host_types`: "all", "app", or "db" (validates host type before execution)
- `agent_command`: Command string with {{.param}} placeholders OR "file:path/to/query.sql" for complex queries
- `backend`: **Hybrid execution routing** (see below)
- `timeout`: Execution timeout in seconds

#### Backend Field - Hybrid Execution Model

The `backend` field supports three formats:

1. **Ansible Execution** (no agent deployment):
   - `ansible.shell` - Execute shell commands via SSH
   - `ansible.database` - Execute database queries via SSH

2. **Go Agent Execution** (requires agent deployment):
   - `agent.shell` - Execute via Go agent HTTP endpoint
   - `agent.soap` - Execute SOAP calls via Go agent
   - `agent.rest` - Execute REST calls via Go agent

3. **Backward Compatibility** (defaults to Go agent):
   - `shell` → same as `agent.shell`
   - `soap` → same as `agent.soap`

**Decision Matrix:**
- Use `ansible.*` for: Simple shell/SQL commands where 100-300ms latency is acceptable
- Use `agent.*` for: SOAP/REST calls, streaming data, or sub-10ms response required

**Current Configuration:**
- Most shell commands: `ansible.shell` (cpu_info, memory_info, disk_usage, etc.)
- Database queries: `ansible.database` (sap_performance_analysis, user_session_analysis)
- SOAP calls: `agent.soap` (get_process_list)

### config/landscape.json
SAP system definitions with 4 SIDs (PRD, QAS, DEV, SBX), each containing:
- `app_servers`: ASCS, PAS, AAS hostnames
- `database.hana_hosts`: HANA database server hostnames
- `ports`, `client`, metadata

### config/ansible_inventory.ini
Ansible inventory defining all SAP hosts:
- Groups: `[prd_app_servers]`, `[prd_db_servers]`, etc.
- Aggregate groups: `[sap_app_servers]`, `[sap_db_servers]`, `[sap_all_servers]`
- Global vars: `ansible_user=sidadm`, SSH connection multiplexing settings
- Auto-generated from landscape.json structure

### config/ansible.cfg
Ansible configuration for SAP environments:
- SSH connection optimization (pipelining, ControlMaster)
- Inventory path, timeout settings
- Performance tuning (gathering, fact_caching)
- Privilege escalation settings

### config/system_prompt
LLM instructions defining:
- SID vs hostname decision logic (3-char = SID, longer = hostname)
- Host type restrictions (app servers vs database servers)
- Workflow patterns for SID resolution
- Command selection based on query type

## Critical Architecture Patterns

### 1. No Singletons - Explicit Dependencies
All components receive dependencies explicitly via constructor:
```python
shared = SharedResources()
shared.initialize()
agent = SAPMonitoringAgent(shared)
```

### 2. Configuration-Driven Commands
Add new commands by editing `config/commands.yaml` - no code changes required. CommandLoader automatically discovers and loads them.

### 3. Hybrid Executor Routing
`ToolExecutor` routes commands based on `backend` field:
```python
# Parse backend: "ansible.shell" → executor=ansible, backend_type=shell
if "." in backend:
    executor, backend_type = backend.split(".", 1)
else:
    executor = "agent"  # Backward compatibility

# Route to appropriate executor
if executor == "ansible":
    result = self.shared.ansible_executor.execute(...)
elif executor == "agent":
    result = self.shared.agent.call_agent_api(...)
```

**Key Design:**
- Single interface for both executors: `execute(server, command, backend, timeout)`
- Transparent switching via configuration
- Graceful degradation if Ansible unavailable

### 4. Host Type Validation
`ToolExecutor` validates commands against host types:
- `get_process_list`, `check_sap_services` → app servers only
- `check_database_status`, `hana_*` commands → database servers only
- `cpu_info`, `memory_info`, `disk_usage` → all servers

### 5. Parallel Tool Execution
ToolExecutor uses ThreadPoolExecutor to run multiple LLM function calls concurrently (max 3 workers).

### 6. Multi-Step Reasoning
SAPMonitoringAgent allows up to 3 reasoning steps per chat turn, enabling workflows like:
1. Get available SIDs → 2. Get app hosts for SID → 3. Check CPU on hosts

### 7. Parameter Substitution
CommandBuilder replaces {{.param}} placeholders with actual values:
```yaml
agent_command: "df -h {{.path}}"  # Becomes: "df -h /hana"
```

### 8. File-Based Commands
Large SQL queries stored in config/queries/:
```yaml
agent_command: "file:config/queries/sap_performance_analysis.sql"
```

## Adding New Monitoring Commands

1. Edit `config/commands.yaml`:
```yaml
my_new_command:
  description: "What this command does"
  params:
    param1: "default_value"
  required: ["server", "param1"]  # server always required for monitoring commands
  allowed_host_types: "app"  # "all", "app", or "db"
  agent_command: "your command here {{.param1}}"
  backend: "ansible.shell"  # Choose: ansible.shell, ansible.database, agent.soap, agent.rest
  timeout: 30
```

2. No code changes needed - restart application and command is available to LLM

**Choosing the Right Backend:**
- `ansible.shell` - Shell commands (top, df, ps, sapcontrol, systemctl)
- `ansible.database` - SQL queries (HANA queries, file-based SQL)
- `agent.soap` - SOAP/RFC calls to SAP systems
- `agent.rest` - REST API calls
- Backward compat: `shell`, `soap`, `database` → defaults to `agent.*`

## Adding New SAP Systems

Edit `config/landscape.json`:
```json
"NEW": {
  "application_sid": "NEW",
  "description": "New System",
  "app_servers": {
    "ascs": ["ascs01.new.local"],
    "pas": ["pas01.new.local"],
    "aas": []
  },
  "database": {
    "hana_sid": "H05",
    "tenant_db": "NEW",
    "hana_hosts": ["hana01.new.local"]
  },
  "ports": {"http": 8000, "https": 44300, "rfc": 3300},
  "client": "100"
}
```

## Vault Integration

**Development**: File-based credentials
- `vault.py` reads `config/vault.json`
- JSON format: `{"azure_openai_api_key": "...", "azure_openai_endpoint": "..."}`
- File gitignored for security

**Production**: Enterprise vault stubs documented in vault.py
- Azure Key Vault integration stub
- HashiCorp Vault integration stub
- AWS Secrets Manager integration stub
- Replace `_load_vault()` method with vault API calls

## Web Server Details

### FastAPI Server (fastapi_server.py)
- **Endpoint**: `POST /chat` - Accepts JSON `{"message": "user query"}`
- **Static files**: Serves `static/index.html` (modern chat UI with markdown rendering)
- **Initialization**: Creates `SharedResources` at startup, initializes all components
- **CORS**: Enabled for cross-origin requests
- **Run**: `python fastapi_server.py` (default: http://localhost:8000)

### Legacy HTTP Server (http_server.py)
- Raw Python HTTP implementation for learning purposes
- Same `/chat` endpoint pattern
- Migration path to FastAPI demonstrated

## SAP-Specific Concepts

### SID (System ID)
Always exactly 3 characters (PRD, QAS, DEV, SBX). Used by LLM to identify which SAP system to query before resolving to actual hostnames.

### Host Types
- **App Servers**: ASCS (Central Services), PAS (Primary Application Server), AAS (Additional Application Servers)
- **Database Servers**: HANA hosts running database services
- **Host type validation**: Commands enforce allowed_host_types to prevent errors (e.g., don't run database commands on app servers)

### SID Resolution Workflow
When user says "Check CPU on PRD":
1. LLM calls `get_app_hosts("PRD")` → returns ["pas01.prd.local", "aas01.prd.local", ...]
2. LLM calls `cpu_info(server="pas01.prd.local")`
3. CommandBuilder builds command, Agent sends to Go agent on pas01.prd.local:8090
4. Response interpreted by LLM

## Hybrid Execution Model Benefits

### Why Hybrid (Ansible + Go Agent)?

**Ansible for Most Commands:**
- ✅ No agent deployment to SAP servers
- ✅ Uses standard SSH (port 22) - already open in most environments
- ✅ Leverages existing SSH key infrastructure
- ✅ Connection pooling reduces latency
- ✅ Rich ecosystem (3000+ modules)
- ✅ Enterprise integration (AWX, Tower, Satellite)

**Go Agent Only When Needed:**
- ✅ SOAP/RFC protocol complexity
- ✅ REST API connection pooling
- ✅ Streaming/real-time data
- ✅ Sub-10ms response requirements

**Result:**
- ~90% of commands use Ansible (no agent deployment)
- ~10% use Go agent (only SOAP/REST)
- Reduced operational overhead
- Easier SAP Basis team approval (SSH vs custom HTTP endpoint)

### Migration Path

Current commands breakdown:
```
Ansible executor (9 commands):
  - cpu_info, memory_info, disk_usage
  - check_database_status, check_sap_services
  - hana_system_overview, hana_process_status, hana_service_status
  - sap_performance_analysis, user_session_analysis

Go agent (1 command):
  - get_process_list (SOAP)

SID resolver (4 functions):
  - get_available_sids, get_all_hosts, get_app_hosts, get_hana_hosts
```

## Key Design Decisions

1. **Hybrid execution model**: Ansible for shell/SQL, Go agent for SOAP/REST
2. **Configuration over code**: Commands, SAP systems, prompts in YAML/JSON
3. **Explicit dependencies**: No hidden globals, all components passed via SharedResources
4. **Real-time accuracy**: No caching of live monitoring data
5. **Host type safety**: Commands validate against allowed server types
6. **Parallel execution**: Multiple function calls executed concurrently
7. **Backend abstraction**: Executor routing via configuration
8. **Production readiness**: Enterprise vault stubs, comprehensive error handling

## Frontend Technologies

The web UI (`static/index.html`) uses vanilla JavaScript with CDN dependencies:
- **Marked.js**: Markdown rendering for LLM responses
- **Highlight.js**: Code syntax highlighting
- **Autosize.js**: Auto-resizing textarea
- No build step required - served directly by FastAPI
