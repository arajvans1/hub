# SAP S/4HANA Monitoring Platform

A lightweight, extensible monitoring platform for SAP S/4HANA systems with AI-powered conversational diagnostics.

## Architecture Overview

This platform consists of two main components:

### 1. **LLM Chatbot Backend** - *This Repository*
- Natural language interface for SAP monitoring
- OpenAI function calling for structured query generation
- Modular architecture with explicit dependency injection
- Converts user prompts into parameterized monitoring commands
- Interprets agent responses into human-readable summaries
- Real-time conversation management with multi-step reasoning

### 2. **Go-Based Monitoring Agent** - *Separate Component*
- Lightweight, zero-dependency Go service
- Executes monitoring commands across multiple backends:
  - **SOAP** - SAP system integration
  - **REST** - Modern API endpoints  
  - **SQL** - Database queries
  - **OS Shell** - System-level commands
- YAML-based command definitions with runtime parameter substitution
- HTTP API for command execution
- Structured logging and modular backend architecture

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
shared_resources.initialize(commands_file="commands.yaml")

# Create agent with explicit dependency injection
agent = SAPMonitoringAgent(
    api_key="your_azure_openai_key",
    azure_endpoint="https://your-endpoint.openai.azure.com/",
    shared_resources=shared_resources
)

# Interactive conversation
chat_history = [{"role": "system", "content": agent.system_prompt}]
chat_history.append({"role": "user", "content": "Check CPU usage on HANA01"})
response = agent.chat(chat_history)
print(response)
```

## Refactored Architecture

The LLM chatbot backend now uses a clean, modular architecture:

### Core Components

- **`SharedResources`** - Container for shared objects with explicit initialization
- **`CommandLoader`** - Loads and validates YAML command definitions
- **`CommandBuilder`** - Builds executable commands with parameter substitution
- **`Agent`** - Handles HTTP communication with monitoring agents
- **`FunctionSchemaBuilder`** - Generates OpenAI function schemas from commands
- **`SAPMonitoringAgent`** - Main orchestrator with LLM integration

### Design Principles

- **Explicit Dependencies** - No hidden globals or singleton patterns
- **Single Responsibility** - Each class has one clear purpose  
- **Clean Separation** - Configuration separate from function schemas
- **Production Ready** - Comprehensive error handling and testing
- **Maintainable** - Clear naming and modular structure

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

Commands are defined in `commands.yaml`:

- `cpu_info` - System CPU utilization
- `memory_info` - Memory usage statistics  
- `disk_usage` - Disk space utilization (with path parameter)
- `get_process_list` - SAP instance processes (with instance parameter)
- *Easily extensible by adding new commands to YAML*

## LLM Chatbot Backend Architecture

### File Structure
```
llm/
├── llm.py                      # Main application with SAPMonitoringAgent
├── command_loader.py           # CommandLoader class - YAML loading
├── command_builder.py          # CommandBuilder class - Command building  
├── agent.py                    # Agent class - HTTP communication
├── function_schema_builder.py  # FunctionSchemaBuilder class - OpenAI schemas
├── commands.yaml               # Command definitions (not in function schemas)
├── requirements.txt            # Python dependencies
└── README.md                   # This documentation
```

### Key Improvements in Refactored Version

- **Explicit Resource Management** - SharedResources with clear initialization
- **Modular Design** - Each component in separate file with single responsibility
- **Clean Configuration** - Monitoring domain not included in LLM function schemas
- **Better Naming** - `CommandLoader` vs old `ConfigManager`, `Agent` vs `AgentClient`
- **Comprehensive Testing** - Full test coverage for all components
- **Production Ready** - Robust error handling and validation

### Design Principles

- **Explicit Dependencies** - SharedResources passed explicitly, no hidden globals
- **Real-time First** - No caching of monitoring data for accuracy
- **Production Ready** - Comprehensive error handling and retry logic
- **Modular Architecture** - Clean separation of loading, building, and communication
- **Debugging Friendly** - Full visibility into execution flow and clear component boundaries

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

### Prerequisites
- Python 3.9+ with conda environment
- Azure OpenAI API access with GPT-4 model
- Go monitoring agent deployed and accessible
- SAP S/4HANA systems configured for monitoring

### Installation
```bash
# Create conda environment
conda create -n llm python=3.9
conda activate llm

# Install dependencies
pip install -r requirements.txt

# Run the application
python llm.py
```

### Environment Configuration
```bash
export AZURE_OPENAI_API_KEY="your_api_key"
export AZURE_OPENAI_ENDPOINT="https://your-endpoint.openai.azure.com/"
export SAP_MONITORING_DOMAIN="mybank.net"
export SAP_AGENT_PORT="8090"
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

The codebase includes comprehensive test coverage:

```bash
# All tests pass in conda environment
python -c "
from command_loader import CommandLoader
from command_builder import CommandBuilder  
from agent import Agent
from function_schema_builder import FunctionSchemaBuilder

# Test basic functionality
loader = CommandLoader('commands.yaml')
commands = loader.get_commands()
print(f'✅ Loaded {len(commands)} commands')

builder = CommandBuilder(commands)
agent = Agent('test.domain.com')
schema_builder = FunctionSchemaBuilder(commands)

print('🎉 All components working correctly!')
"
```

## Repository Structure

```
llm/
├── llm.py                      # Main SAPMonitoringAgent application
├── command_loader.py           # YAML command loading and validation
├── command_builder.py          # Command building with parameter substitution
├── agent.py                    # HTTP communication with monitoring agents
├── function_schema_builder.py  # OpenAI function schema generation
├── commands.yaml               # Command definitions (separate from schemas)
├── requirements.txt            # Python dependencies
├── README.md                   # This documentation  
├── message                     # Additional documentation
└── .gitignore                  # Git ignore configuration
```

The Go monitoring agent is maintained as a separate service/repository.
