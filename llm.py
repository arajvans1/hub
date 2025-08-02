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
# Prompt Template
# ------------------------
def build_command_help():
    help_lines = [
        f"- {cmd}: {spec['description']}, params: {spec['params']}"
        for cmd, spec in COMMAND_SPECS.items()
    ]
    return "\n".join(help_lines).replace("{", "{{").replace("}", "}}")

command_help = build_command_help()

base_prompt_template = ChatPromptTemplate.from_template(f"""
You are a SAP Monitoring Assistant.

You can call the tool:

monitoring(server: str, command: str, params: dict)

Available commands:

{command_help}

Instructions:
1. If monitoring tool is needed, output ONLY JSON in this format:
   {{{{
     "action": "monitoring",
     "server": "<server>",
     "command": "<command>",
     "params": {{{{}}}}
   }}}}
2. Otherwise, respond in plain English.

Conversation so far:
{{history}}

User: {{user_input}}
Context: {{context}}
""")

parser = JsonOutputParser()

# ------------------------
# Multi-Turn Agent with Memory
# ------------------------
def agent_step(user_input: str, chat_history: list, max_steps: int = 3):
    """
    chat_history: list of {"role": "user"/"assistant", "content": str}
    """
    # Build history text for the prompt
    history_text = "\n".join(f"{m['role'].capitalize()}: {m['content']}" for m in chat_history)
    context = ""  # additional tool results per loop

    for step in range(max_steps):
        messages = base_prompt_template.format_messages(
            user_input=user_input,
            history=history_text,
            context=context or "None"
        )

        llm_response = llm.invoke(messages)
        content = llm_response.content.strip()

        # Step 1: Try to parse as tool action
        try:
            action = parser.parse(content)
            if action.get("action") == "monitoring":
                server = action["server"]
                command = action["command"]
                params = action.get("params", {}) or {}

                if not validate_command(command, params):
                    return f"Invalid command or params: {command} {params}"

                # Step 2: Execute tool
                result = monitoring(server, command, params)
                context += f"\nTool called: {server}/{command} {params} → {result}"
                continue  # Let LLM reason again with result in context

        except Exception:
            # Not a JSON action → final answer
            chat_history.append({"role": "assistant", "content": content})
            return content

    return f"Max reasoning steps reached without final answer."

# ------------------------
# Example Multi-Turn Conversation
# ------------------------
if __name__ == "__main__":
    chat_history = []
    while True:
        user_input = input("User: ")
        if user_input.lower() in ["exit", "quit"]:
            break

        output = agent_step(user_input, chat_history)
        chat_history.append({"role": "user", "content": user_input})
        chat_history.append({"role": "assistant", "content": output})
        print("Assistant:", output)
      
   

