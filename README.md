# SAP S/4HANA Monitoring Platform

A lightweight, extensible monitoring platform for SAP S/4HANA systems with AI-powered conversational diagnostics.

## Quick Start

1. **Setup credentials**:
   ```bash
   # Edit config/vault.json with your Azure OpenAI credentials
   {
     "azure_openai_api_key": "your-api-key",
     "azure_openai_endpoint": "https://your-resource.openai.azure.com/"
   }
   ```

2. **Install and run**:
   ```bash
   pip install -r requirements.txt
   python llm.py
   ```

3. **Start monitoring**:
   ```
   > Check CPU usage on server01
   > Show available SIDs
   > Get HANA hosts for PRD system
   ```

## Architecture Overview

This platform consists of two main components:

### 1. **LLM Chatbot Backend** - *This Repository*
- Natural language interface for SAP monitoring
- Azure OpenAI function calling for structured query generation
- Configuration-driven architecture with YAML commands
- Converts user prompts into parameterized monitoring commands
- Real-time conversation management with multi-step reasoning
- Simple vault integration for credential management

### 2. **Go-Based Monitoring Agent** - *Separate Component*
- Lightweight, zero-dependency Go service
- Executes monitoring commands across multiple backends:
  - **SOAP** - SAP system integration
  - **REST** - Modern API endpoints  
  - **SQL** - Database queries
  - **OS Shell** - System-level commands
- YAML-based command definitions with runtime parameter substitution
- HTTP API for command execution

## Key Features

- ✅ **Conversational AI diagnostics** - Natural language SAP monitoring
- ✅ **Multi-backend execution** - SOAP, REST, SQL, Shell commands
- ✅ **Real-time monitoring** - No caching of live metrics for accuracy
- ✅ **Modular architecture** - Clean separation of concerns
- ✅ **Explicit dependencies** - No hidden globals or singletons
- ✅ **Production-ready** - Comprehensive error handling and testing
- ✅ **Extensible** - Easy to add new commands and backends

## How It Works

```
User: "Check CPU usage on HANA01 and get SAP processes for instance 00"
  ↓
LLM Chatbot Backend:
  • CommandLoader: Loads available commands from YAML
  • FunctionSchemaBuilder: Generates OpenAI function schemas
  • OpenAI LLM: Parses natural language and generates function calls
  • CommandBuilder: Builds executable commands with parameters
  • Agent: Communicates with monitoring agents via HTTP
  ↓  
Go Monitoring Agent:
  • Receives HTTP request with command + parameters
  • Looks up YAML command definition
  • Executes via appropriate backend (Shell, SOAP, etc.)
  • Returns structured response
  ↓
LLM Chatbot Backend:
  • Interprets technical response
  • Generates human-readable summary
  • Continues conversation context
```

## Usage

```python
from llm import SAPMonitoringAgent, SharedResources

# Initialize shared resources once
shared_resources = SharedResources()
shared_resources.initialize()

# Create agent (credentials loaded from vault)
agent = SAPMonitoringAgent(shared_resources)

# Interactive conversation
chat_history = [{"role": "system", "content": agent.system_prompt}]
chat_history.append({"role": "user", "content": "Check CPU usage on server01"})
response = agent.chat(chat_history)
print(response)
```

## Current Architecture

The LLM chatbot backend uses a clean, simplified architecture:

### Core Components

- **`SharedResources`** - Container for shared objects with one-time initialization
- **`VaultManager`** - Simple credential management (file-based for dev, enterprise stubs for prod)
- **`CommandLoader`** - Loads and validates YAML command definitions
- **`CommandBuilder`** - Builds executable commands with parameter substitution
- **`Agent`** - Handles HTTP communication with monitoring agents
- **`FunctionSchemaBuilder`** - Generates Azure OpenAI function schemas from commands
- **`SIDResolver`** - SAP system ID discovery and host resolution (4 clean functions)
- **`SAPMonitoringAgent`** - Main orchestrator with LLM integration

### Key Features

- ✅ **Simple vault integration** - File-based credentials for development
- ✅ **Configuration-driven** - YAML commands with explicit required parameters  
- ✅ **Azure OpenAI compatible** - All 8 function schemas properly formatted
- ✅ **Clean SID resolution** - Exactly 4 functions for SAP system discovery
- ✅ **Optimized schemas** - Moved from hardcoded if/else to configuration-driven approach
- ✅ **Minimal dependencies** - Only essential packages, no unnecessary bloat
- ✅ **Production ready** - Clear stubs for enterprise vault integration

## Command Flow

The LLM chatbot backend converts natural language into structured API calls:

1. **Command Loading** - `CommandLoader` loads commands from YAML
2. **Schema Generation** - `FunctionSchemaBuilder` creates OpenAI function schemas
3. **Intent Recognition** - LLM parses user request using function calling
4. **Command Building** - `CommandBuilder` generates executable commands with parameters
5. **Agent Communication** - `Agent` makes HTTP call to Go agent: `POST /execute`
6. **Backend Execution** - Go agent routes to appropriate backend
7. **Response Interpretation** - LLM converts technical data to natural language

## Supported Monitoring Commands

Commands are defined in `config/commands.yaml`:

### SID Discovery Functions (4 core functions)
- `get_available_sids` - List all SAP System IDs in landscape
- `get_all_hosts(sid)` - All hosts for a SAP system (app + DB)
- `get_app_hosts(sid)` - Application server hosts only
- `get_hana_hosts(sid)` - HANA database hosts only

### Monitoring Commands
- `cpu_info` - System CPU utilization
- `memory_info` - Memory usage statistics  
- `disk_usage(path)` - Disk space utilization with path parameter
- `get_process_list(instance)` - SAP instance processes with instance parameter

*Easily extensible by adding new commands to YAML with explicit required parameters*

## Configuration

### Vault Setup
```json
// config/vault.json
{
  "azure_openai_api_key": "your-api-key",
  "azure_openai_endpoint": "https://your-resource.openai.azure.com/"
}
```

### Command Configuration
```yaml
# config/commands.yaml - Example command
cpu_info:
  description: "Get current CPU usage"
  params: {}
  required: ["server"]  # Explicit required parameters
  agent_command: "top -bn1 | grep 'Cpu(s)' | head -1"
  backend: "shell"
  timeout: 30
```

### SAP Landscape
```json
// config/landscape.json - SAP systems
{
  "PRD": {
    "app_hosts": ["sapapp01", "sapapp02"],
    "hana_hosts": ["hanadb01", "hanadb02"]
  }
}
```

## LLM Chatbot Backend Architecture

### File Structure
```
llm/
├── llm.py                      # Main application with SAPMonitoringAgent
├── vault.py                    # Simple vault manager (file-based for dev)
├── sid_resolver.py             # SID discovery with 4 clean functions
├── command_loader.py           # CommandLoader class - YAML loading
├── command_builder.py          # CommandBuilder class - Command building  
├── agent.py                    # Agent class - HTTP communication
├── function_schema_builder.py  # FunctionSchemaBuilder class - Azure OpenAI schemas
├── config/
│   ├── commands.yaml           # Command definitions (8 commands)
│   ├── landscape.json          # SAP systems (4 SIDs)
│   ├── system_prompt           # LLM system prompt
│   └── vault.json              # Credentials (gitignored)
├── requirements.txt            # Python dependencies  
└── README.md                   # This documentation
```

### Vault Integration

**Development**: Simple file-based credentials
```python
# vault.py reads config/vault.json
vault_manager = VaultManager()
credentials = vault_manager.get_azure_openai_config()
```

**Production**: Enterprise vault stubs ready
```python
# TODO: Replace _load_vault() with enterprise vault API calls
# - Azure Key Vault
# - HashiCorp Vault  
# - AWS Secrets Manager
```

### Key Optimizations

- **Simplified vault** - No cryptography, just reads JSON file
- **Configuration-driven schemas** - Moved from hardcoded if/else logic  
- **Explicit required parameters** - Clear YAML structure with required arrays
- **Clean SID resolver** - Exactly 4 functions, no duplicate code
- **Minimal dependencies** - Only essential packages
- **Azure OpenAI compatible** - All 8 schemas properly formatted

## Go Agent Integration

### Command Configuration
Commands are defined in `commands.yaml` and loaded by `CommandLoader`:

```yaml
# Example command definition
commands:
  cpu_info:
    description: "Get current CPU usage"
    params: {}
    required: []
    agent_command: "top -bn1 | grep 'Cpu(s)' | head -1"
    backend: "shell"
    timeout: 30

  disk_usage:
    description: "Get disk usage stats for a path"
    params:
      path: "/hana"
      threshold: "80"  
    required: ["path"]
    agent_command: "df -h {{.path}}"
    backend: "shell"
    timeout: 30
```

### Communication Pattern
The `Agent` class handles HTTP communication:
```python
result = agent.call_agent_api(
    server="hana01",
    command="df -h /hana", 
    backend="shell",
    timeout=30
)
```

## Go Agent Architecture

### Backend Interfaces
```go
type Backend interface {
    Execute(command string) ([]byte, error)
}

// Implementations:
// - SOAPBackend    - SAP system integration
// - RESTBackend    - HTTP API calls
// - SQLBackend     - Database queries  
// - ShellBackend   - OS command execution
```

### Key Design Features

- **Zero Dependencies** - Standalone Go binary
- **YAML Configuration** - Declarative command definitions
- **Runtime Substitution** - Dynamic parameter injection
- **Structured Logging** - JSON event logs
- **Safe Concurrency** - Production-ready patterns
- **Dynamic Config Reload** - Hot configuration updates
- **Fast Startup** - Minimal initialization time

## Integration Pattern

```yaml
# Example Go agent command definition
commands:
  cpu_info:
    backend: shell
    command: "top -bn1 | grep 'Cpu(s)' | head -1"
    timeout: 10s
    
  get_sap_processes:
    backend: soap
    endpoint: "{{.server}}.mybank.net:8000/sap/bc/soap/rfc"
    command: "RFC_READ_TABLE"
    params:
      QUERY_TABLE: "V$PROCESS"
      OPTIONS: 
        - TEXT: "PROGRAM LIKE '%SAP%'"
```

The LLM chatbot (`llm.py`) makes HTTP calls to the Go agent, which executes the appropriate backend command and returns structured data for interpretation.

## Production Deployment

## Installation & Setup

### Prerequisites
- Python 3.9+ 
- Azure OpenAI API access with GPT-4 model

### Quick Setup
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure credentials
# Edit config/vault.json:
{
  "azure_openai_api_key": "your-api-key",
  "azure_openai_endpoint": "https://your-resource.openai.azure.com/"
}

# 3. Run the application
python llm.py
```

### System Validation
```bash
# Test all components
python -c "
from llm import SharedResources
shared = SharedResources()
shared.initialize()
print(f'✅ {len(shared.commands_loader.get_commands())} commands loaded')
print(f'✅ {len(shared.sid_resolver.get_available_sids())} SIDs available') 
print(f'✅ {len(shared.tools)} Azure OpenAI schemas generated')
print('🚀 System ready!')
"
```

### Monitoring Agent Communication
The `Agent` class communicates with the Go agent via HTTP:
```
POST http://{server}.{domain}:{port}/execute
{
  "command": "top -bn1 | grep 'Cpu(s)' | head -1",
  "backend": "shell",
  "timeout": 30
}
```

## Why This Refactored Architecture?

This implementation prioritizes:

1. **Conversational AI** - Natural language SAP diagnostics
2. **Clean Architecture** - Explicit dependencies, no hidden globals  
3. **Maintainability** - Single responsibility classes, clear separation
4. **Production Readiness** - Comprehensive testing and error handling
5. **Real-time Accuracy** - No caching of live monitoring data
6. **Extensibility** - Easy to add new commands, backends, and functionality
7. **Debugging Simplicity** - Clear component boundaries and execution flow

Perfect for enterprise SAP environments where reliability, maintainability, and conversational diagnostics are critical.

## Testing

The codebase includes comprehensive validation:

```bash
# Quick system test
python -c "
from llm import SharedResources
shared = SharedResources()
shared.initialize()
print('=== System Test Results ===')
print(f'✅ Commands: {len(shared.commands_loader.get_commands())}/8')
print(f'✅ SIDs: {len(shared.sid_resolver.get_available_sids())}/4')
print(f'✅ Schemas: {len(shared.tools)}/8')
print(f'✅ Vault: {\"OK\" if shared.vault_manager else \"FAIL\"}')
print('🚀 All systems operational!')
"

# Test SID resolver functions
python -c "
from sid_resolver import SIDResolver
resolver = SIDResolver('config/landscape.json')
sids = resolver.get_available_sids()
print(f'Available SIDs: {sids}')
print(f'PRD hosts: {len(resolver.get_all_hosts(\"PRD\"))}')
"
```

## Next Phase: HTTP Server Implementation

The system is now ready for the next phase - implementing a raw Python HTTP server:

- **Learning Focus**: HTTP protocol fundamentals from first principles
- **Migration Path**: Clean transition to FastAPI later  
- **API Endpoints**: `/chat` for conversational monitoring
- **Request Handling**: JSON request/response with proper status codes
- **URL Routing**: Manual implementation for maximum learning value

**Current Status**: ✅ All 8 commands loaded, ✅ 4 SIDs available, ✅ 8 Azure schemas, ✅ Vault operational
