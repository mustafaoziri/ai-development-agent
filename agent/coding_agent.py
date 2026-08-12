import json
import os

from openai import OpenAI

from tools import (
    list_files,
    read_file,
    write_file,
    run_command
)

from prompts import SYSTEM_PROMPT


client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY")
)


TOOLS = [
    {
        "type": "function",
        "name": "list_files",
        "description": "List all files in the current project.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "type": "function",
        "name": "read_file",
        "description": "Read the contents of a project file.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path of the file."
                }
            },
            "required": ["path"]
        }
    },
    {
        "type": "function",
        "name": "write_file",
        "description": "Create or update a project file.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path of the file."
                },
                "content": {
                    "type": "string",
                    "description": "Complete file content."
                }
            },
            "required": ["path", "content"]
        }
    },
    {
        "type": "function",
        "name": "run_command",
        "description": "Run a terminal command inside the project.",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Terminal command to execute."
                }
            },
            "required": ["command"]
        }
    }
]


def execute_tool(name, arguments):

    if name == "list_files":
        return list_files()

    if name == "read_file":
        return read_file(arguments["path"])

    if name == "write_file":
        return write_file(
            arguments["path"],
            arguments["content"]
        )

    if name == "run_command":
        return run_command(arguments["command"])

    return f"Unknown tool: {name}"


def run_agent(requirements):

    print("\n=== CODING AGENT STARTED ===\n")

    response = client.responses.create(
        model="openai/gpt-oss-120b",
        instructions=SYSTEM_PROMPT,
        input=requirements,
        tools=TOOLS
    )

    while True:

        tool_outputs = []

        for item in response.output:

            if item.type != "function_call":
                continue

            name = item.name

            arguments = json.loads(item.arguments)

            print(f"[TOOL] {name}")
            print(f"[ARGS] {arguments}\n")

            result = execute_tool(
                name,
                arguments
            )

            tool_outputs.append(
                {
                    "type": "function_call_output",
                    "call_id": item.call_id,
                    "output": result
                }
            )

        if not tool_outputs:
            break

        response = client.responses.create(
            model="openai/gpt-oss-120b",
            previous_response_id=response.id,
            input=tool_outputs,
            tools=TOOLS
        )

    print("\n=== CODING AGENT FINISHED ===\n")

    print(response.output_text)

    return response.output_text


if __name__ == "__main__":

    requirements = """
    Create a simple customer registration web application.

    Requirements:

    - Use Python and Flask.
    - Use SQLite for storage.
    - Create a simple web interface.
    - The user should enter:
      - Full name
      - Email
      - Phone number
    - Provide a Register button.
    - Save registered customers to SQLite.
    - Show a success message after registration.
    - Keep the UI simple and clean.
    """

    run_agent(requirements)