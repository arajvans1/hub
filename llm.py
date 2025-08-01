from langchain_openai import AzureChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
import requests

# ------------------------
# Monitoring Tool
# ------------------------
MONITORING_DOMAIN = "mybank.net"

def monitoring(server: str, command: str, params: dict = None) -> dict:
    """Fetch system metrics from SAP server monitoring agent."""
    if params is None:
        params = {}
    try:
        url = f"http://{server}.{MONITORING_DOMAIN}:8090/execute"
        payload = {"name": command, "params": params}
        response = requests.post(url, json=payload, timeout=5)
        return response.json()
    except Exception as e:
        return {"error": str(e)}

# ------------------------
# Define Available Commands
# ------------------------
COMMAND_SPECS = {
    "cpu": {
        "description": "Get current CPU usage",
        "params": {}  # no extra params
    },
    "memory": {
        "description": "Get current memory usage",
        "params": {}
    },
    "get_process_list": {
        "description": "Get list of running processes for a given instance",
        "params": {"instance": "00"}  # example param
    },
    "disk_usage": {
        "description": "Get disk usage stats for a mount point",
        "params": {"mount": "/hana"}  # example param
    }
}

# ------------------------
# Generate Safe Command Help for Prompt
# ------------------------
command_help = "\n".join(
    f"- {cmd}: {spec['description']}, params: {spec['params']}"
    for cmd, spec in COMMAND_SPECS.items()
)
# Escape { and } for LangChain templates
command_help = command_help.replace("{", "{{").replace("}", "}}")

# ------------------------
# Prompt Template
# ------------------------
prompt_template = ChatPromptTemplate.from_template(f"""
You are a SAP Monitoring Assistant.

You can call the tool:

monitoring(server: str, command: str, params: dict)

Here are the available commands and their required params:

{command_help}

When the user asks something requiring data from servers:
1. Pick the correct command
2. Populate the params exactly as shown in the examples
3. Output ONLY JSON in this format:

{{{{
  "action": "monitoring",
  "server": "<server>",
  "command": "<command>",
  "params": {{{{}}}} 
}}}}

If no monitoring call is needed, respond in plain English.

User: {{user_input}}
""")

parser = JsonOutputParser()

# ------------------------
# Validate Command Helper
# ------------------------
def validate_command(command: str, params: dict) -> bool:
    """Check if the command and params are valid per COMMAND_SPECS."""
    if command not in COMMAND_SPECS:
        return False
    expected_keys = set(COMMAND_SPECS[command]["params"].keys())
    provided_keys = set(params.keys())
    # All expected keys must exist, extra keys are allowed
    return expected_keys.issubset(provided_keys)

# ------------------------
# Agent Step Function
# ------------------------
def agent_step(user_input: str):
    # 1. Ask LLM to generate a tool call or direct answer
    messages = prompt_template.format_messages(user_input=user_input)
    llm_response = llm.invoke(messages)
    content = llm_response.content.strip()

    # 2. Try parsing JSON for tool invocation
    try:
        action = parser.parse(content)
        if action.get("action") == "monitoring":
            server = action["server"]
            command = action["command"]
            params = action.get("params", {}) or {}

            # Validate command + params
            if not validate_command(command, params):
                return f"Invalid command or params: {command} {params}"

            # 3. Execute monitoring
            result = monitoring(server, command, params)

            # 4. Final step: turn tool output into user-friendly text
            final_prompt = f"""
User asked: {user_input}
I called monitoring({server}, {command}, {params}) and got result: {result}
Answer the user in clear natural language.
"""
            final_response = llm.invoke(final_prompt)
            return final_response.content

    except Exception:
        # No valid JSON → just return LLM response
        return content

# ------------------------
# LLM Init
# ------------------------
llm = AzureChatOpenAI(
    api_key="YOUR_KEY",
    api_version="2024-08-01",
    azure_endpoint="https://your-endpoint.openai.azure.com/",
    model="gpt-4",
)

# ------------------------
# Test
# ------------------------
print(agent_step("Show process list for server hana01 instance 02"))
