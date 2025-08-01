from langchain_openai import AzureChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
import requests

# ------------------------
# Configuration
# ------------------------
MONITORING_DOMAIN = "mybank.net"

COMMAND_SPECS = {
    "cpu": {"description": "Get current CPU usage", "params": {}},
    "memory": {"description": "Get current memory usage", "params": {}},
    "get_process_list": {
        "description": "Get list of running processes for a given instance",
        "params": {"instance": "00"}
    },
    "disk_usage": {
        "description": "Get disk usage stats for a mount point",
        "params": {"mount": "/hana"}
    }
}

# ------------------------
# LLM Initialization
# ------------------------
llm = AzureChatOpenAI(
    api_key="YOUR_KEY",
    api_version="2024-08-01",
    azure_endpoint="https://your-endpoint.openai.azure.com/",
    model="gpt-4",
)

# ------------------------
# Utility Functions
# ------------------------
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

def validate_command(command: str, params: dict) -> bool:
    """Check if the command and params are valid per COMMAND_SPECS."""
    if command not in COMMAND_SPECS:
        return False
    expected_keys = set(COMMAND_SPECS[command]["params"].keys())
    provided_keys = set(params.keys())
    return expected_keys.issubset(provided_keys)

# ------------------------
# Prompt Template Setup
# ------------------------
def build_command_help():
    help_lines = [
        f"- {cmd}: {spec['description']}, params: {spec['params']}"
        for cmd, spec in COMMAND_SPECS.items()
    ]
    help_text = "\n".join(help_lines)
    return help_text.replace("{", "{{").replace("}", "}}")

command_help = build_command_help()

base_prompt_template = ChatPromptTemplate.from_template(f"""
You are a SAP Monitoring Assistant.

You can call the tool:

monitoring(server: str, command: str, params: dict)

Available commands:

{command_help}

Your job:
1. Decide if a monitoring tool call is needed
2. Output ONLY JSON if tool is needed:
   {{{{
     "action": "monitoring",
     "server": "<server>",
     "command": "<command>",
     "params": {{{{}}}}
   }}}}
3. Otherwise, respond in plain English.

User: {{user_input}}
Context: {{context}}
""")

parser = JsonOutputParser()

# ------------------------
# Multi-Step Agent Logic
# ------------------------
def agent_loop(user_input: str, max_steps: int = 5):
    context = ""
    for step in range(max_steps):
        # Step 1: Ask LLM
        messages = base_prompt_template.format_messages(
            user_input=user_input,
            context=context or "None yet"
        )
        llm_response = llm.invoke(messages)
        content = llm_response.content.strip()

        # Step 2: Try parsing JSON for tool invocation
        try:
            action = parser.parse(content)
            if action.get("action") == "monitoring":
                server = action["server"]
                command = action["command"]
                params = action.get("params", {}) or {}

                # Validate command + params
                if not validate_command(command, params):
                    return f"Invalid command or params: {command} {params}"

                # Step 3: Execute monitoring
                result = monitoring(server, command, params)
                # Add result to context for next reasoning step
                context += f"\nTool called: {server}/{command} {params} → {result}"

                continue  # LLM can reason again

        except Exception:
            # No valid JSON → treat as final answer
            return content

        # If LLM did not produce a tool call → it's the final answer
        return content

    return f"Max steps {max_steps} reached without final answer."


# ------------------------
# Test
# ------------------------
if __name__ == "__main__":
    # Example: Multi-step reasoning
    query = "Check CPU on hana01 and memory on hana02"
    print(agent_loop(query))
