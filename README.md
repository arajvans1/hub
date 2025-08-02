# SAP S/4HANA Monitoring Platform

A lightweight, extensible monitoring platform for SAP S/4HANA systems with AI-powered conversational diagnostics.

## Architecture Overview

This platform consists of two main components:

### 1. **LLM Chatbot (`llm.py`)** - *This Repository*
- Natural language interface for SAP monitoring
- OpenAI function calling for structured query generation
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
- ✅ **Declarative commands** - YAML-defined monitoring operations
- ✅ **Production-ready** - Fast startup, dynamic config reload, safe concurrency
- ✅ **Zero external dependencies** - Lightweight Go agent design

## How It Works

```
User: "Check CPU usage on HANA01 and get SAP processes for instance 00"
  ↓
LLM Chatbot (llm.py):
  • Parses natural language intent
  • Uses OpenAI function calling to generate structured commands
  • Calls Go agent HTTP API with parameters
  ↓  
Go Monitoring Agent:
  • Receives HTTP request with command + parameters
  • Looks up YAML command definition
  • Executes via appropriate backend (Shell, SOAP, etc.)
  • Returns structured response
  ↓
LLM Chatbot (llm.py):
  • Interprets technical response
  • Generates human-readable summary
  • Continues conversation context
```

## Usage

```python
from llm import SAPMonitoringAgent

agent = SAPMonitoringAgent(
    api_key="your_azure_openai_key",
    azure_endpoint="https://your-endpoint.openai.azure.com/"
)

# Interactive conversation
chat_history = [{"role": "system", "content": agent.system_prompt}]
chat_history.append({"role": "user", "content": "Check CPU usage on HANA01"})
response = agent.chat(chat_history)
print(response)
```

## Command Flow

The LLM chatbot converts natural language into structured API calls:

1. **Intent Recognition** - Parse user request
2. **Function Calling** - Generate structured command with parameters
3. **Agent Communication** - HTTP call to Go agent: `POST /execute`
4. **Backend Execution** - Agent routes to appropriate backend
5. **Response Interpretation** - Convert technical data to natural language

## Supported Monitoring Commands

- `cpu_info` - System CPU utilization
- `memory_info` - Memory usage statistics  
- `disk_usage` - Disk space utilization
- `get_process_list` - SAP instance processes
- *Extensible via YAML configuration in Go agent*

## LLM Chatbot Architecture (`llm.py`)

### Core Components

- **`COMMAND_SPECS`** - Single source of truth for available monitoring commands
- **OpenAI Function Calling** - Robust parameter extraction and validation
- **Multi-step Reasoning** - Handles complex monitoring workflows
- **Real-time Communication** - Direct HTTP calls to Go agent (no caching)

### Design Principles

- **Manual Control** - No heavy frameworks, direct OpenAI API usage
- **Real-time First** - No caching of monitoring data for accuracy
- **Production Ready** - Comprehensive error handling and retry logic
- **Debugging Friendly** - Full visibility into execution flow

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
- Azure OpenAI API access with GPT-4 model
- Go monitoring agent deployed and accessible
- SAP S/4HANA systems configured for monitoring

### Environment Configuration
```bash
export AZURE_OPENAI_API_KEY="your_api_key"
export AZURE_OPENAI_ENDPOINT="https://your-endpoint.openai.azure.com/"
export SAP_MONITORING_DOMAIN="mybank.net"
export SAP_AGENT_PORT="8090"
```

### Monitoring Agent Communication
The LLM chatbot communicates with the Go agent via HTTP:
```
POST http://{server}.{domain}:{port}/execute
{
  "name": "cpu_info",
  "params": {"server": "hana01"}
}
```

## Why This Architecture?

This implementation prioritizes:

1. **Conversational AI** - Natural language SAP diagnostics
2. **Real-time Accuracy** - No caching of live monitoring data
3. **Modular Design** - Separate LLM logic from monitoring execution
4. **Production Readiness** - Zero dependencies, fast startup, safe concurrency
5. **Extensibility** - Easy to add new backends and commands
6. **Debugging Simplicity** - Clear separation of concerns and full visibility

Perfect for enterprise SAP environments where reliability, transparency, and conversational diagnostics are critical.

## Repository Structure

```
llm/
├── llm.py              # LLM chatbot implementation (this repo)
├── README.md           # This documentation
├── .gitignore         # Ignore analysis/test files
└── [analysis files]   # Excluded from version control
```

The Go monitoring agent is maintained as a separate service/repository.
