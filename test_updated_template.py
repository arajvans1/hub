from langchain_core.prompts import ChatPromptTemplate

# Test the updated template
def build_command_help():
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

# Test the template
try:
    messages = base_prompt_template.format_messages(
        user_input="Check CPU on hana01 and memory on hana02",
        context="None yet"
    )
    print("✅ Template parsing is working perfectly!")
    print("Generated message (first 500 chars):")
    print(messages[0].content[:500] + "...")
    
except Exception as e:
    print(f"❌ Template parsing failed: {e}")
    print(f"Error type: {type(e)}")
