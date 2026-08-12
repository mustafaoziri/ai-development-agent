import json
import os
import time

from dotenv import load_dotenv
from openai import (
    OpenAI,
    APIConnectionError,
    APITimeoutError,
    InternalServerError,
    RateLimitError,
)

from tools import (
    list_files,
    read_file,
    write_file,
    run_command,
)

from prompts import SYSTEM_PROMPT


# --------------------------------------------------
# Environment
# --------------------------------------------------

load_dotenv()


GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")

MAX_AGENT_ITERATIONS = int(
    os.getenv("MAX_AGENT_ITERATIONS", "20")
)

MAX_TOOL_OUTPUT_LENGTH = int(
    os.getenv("MAX_TOOL_OUTPUT_LENGTH", "10000")
)

REASONING_EFFORT = os.getenv(
    "REASONING_EFFORT",
    "medium"
)


if not GROQ_API_KEY:
    raise RuntimeError(
        "GROQ_API_KEY is not set. "
        "Add it to your .env file."
    )


# --------------------------------------------------
# Groq / OpenAI-compatible client
# --------------------------------------------------

client = OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1",
    timeout=120.0,
)


# --------------------------------------------------
# Tools
# --------------------------------------------------

TOOLS = [
    {
        "type": "function",
        "name": "list_files",
        "description": (
            "List all files in the current project. "
            "Use this to inspect the project structure."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },

    {
        "type": "function",
        "name": "read_file",
        "description": (
            "Read the contents of a project file. "
            "The path must be relative to the project directory."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": (
                        "Relative path of the file "
                        "inside the project."
                    ),
                },
            },
            "required": ["path"],
        },
    },

    {
        "type": "function",
        "name": "write_file",
        "description": (
            "Create or update a project file. "
            "Provide the complete file content."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": (
                        "Relative path of the file "
                        "inside the project."
                    ),
                },
                "content": {
                    "type": "string",
                    "description": (
                        "Complete content of the file."
                    ),
                },
            },
            "required": ["path", "content"],
        },
    },

    {
        "type": "function",
        "name": "run_command",
        "description": (
            "Run a terminal command inside the project "
            "directory. Use this to install dependencies, "
            "run tests, start applications, or inspect "
            "the project."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": (
                        "Terminal command to execute."
                    ),
                },
            },
            "required": ["command"],
        },
    },
]


# --------------------------------------------------
# Tool execution
# --------------------------------------------------

def execute_tool(name, arguments):

    try:

        if name == "list_files":
            result = list_files()

        elif name == "read_file":
            result = read_file(arguments["path"])

        elif name == "write_file":
            result = write_file(
                arguments["path"],
                arguments["content"],
            )

        elif name == "run_command":
            result = run_command(arguments["command"])

        else:
            result = f"Unknown tool: {name}"

        # Prevent huge tool outputs from consuming
        # the entire context window.
        if len(result) > MAX_TOOL_OUTPUT_LENGTH:
            result = (
                result[:MAX_TOOL_OUTPUT_LENGTH]
                + "\n\n[TOOL OUTPUT TRUNCATED]"
            )

        return result

    except Exception as exc:

        # Important:
        # Do not crash the entire agent when a tool fails.
        # Instead, tell the model what went wrong so
        # it can attempt to recover.
        return (
            f"Tool '{name}' failed.\n"
            f"Error type: {type(exc).__name__}\n"
            f"Error: {exc}"
        )


# --------------------------------------------------
# API call with retry
# --------------------------------------------------

def create_response(input_data, instructions=None):

    max_retries = 3

    for attempt in range(max_retries):

        try:

            kwargs = {
                "model": MODEL,
                "input": input_data,
                "tools": TOOLS,
                "reasoning": {
                    "effort": REASONING_EFFORT
                },
            }

            if instructions is not None:
                kwargs["instructions"] = instructions

            return client.responses.create(**kwargs)

        except (
            APIConnectionError,
            APITimeoutError,
            InternalServerError,
            RateLimitError,
        ) as exc:

            if attempt == max_retries - 1:
                raise

            wait_time = 2 ** attempt

            print(
                f"\n[API ERROR] {type(exc).__name__}"
            )

            print(
                f"[RETRY] Retrying in {wait_time}s...\n"
            )

            time.sleep(wait_time)


# --------------------------------------------------
# Agent
# --------------------------------------------------

def run_agent(requirements):

    print("\n=== CODING AGENT STARTED ===")
    print(f"Model: {MODEL}")
    print(
        f"Max iterations: {MAX_AGENT_ITERATIONS}"
    )
    print(
        f"Reasoning: {REASONING_EFFORT}\n"
    )

    # Groq Responses API currently does not support
    # previous_response_id.
    #
    # Therefore, we maintain the conversation ourselves.
    conversation = [
        {
            "role": "user",
            "content": requirements,
        }
    ]

    response = create_response(
        input_data=conversation,
        instructions=SYSTEM_PROMPT,
    )

    iteration = 0

    while iteration < MAX_AGENT_ITERATIONS:

        iteration += 1

        print(
            f"\n--- Agent iteration "
            f"{iteration}/{MAX_AGENT_ITERATIONS} ---"
        )

        tool_outputs = []

        for item in response.output:

            if item.type != "function_call":
                continue

            name = item.name

            try:
                arguments = json.loads(
                    item.arguments
                )
            except json.JSONDecodeError:

                print(
                    f"[ERROR] Invalid JSON arguments "
                    f"from model for tool '{name}'"
                )

                tool_outputs.append(
                    {
                        "type": "function_call_output",
                        "call_id": item.call_id,
                        "output": (
                            "Invalid JSON arguments. "
                            "Please provide valid JSON "
                            "arguments and try again."
                        ),
                    }
                )

                continue

            print(f"[TOOL] {name}")
            print(f"[ARGS] {arguments}\n")

            result = execute_tool(
                name,
                arguments,
            )

            print("[RESULT]")
            print(result[:2000])

            if len(result) > 2000:
                print("...")

            print()

            tool_outputs.append(
                {
                    "type": "function_call_output",
                    "call_id": item.call_id,
                    "output": result,
                }
            )

        # --------------------------------------------------
        # No tool calls = model has finished
        # --------------------------------------------------

        if not tool_outputs:

            print(
                "\n=== AGENT FINISHED ===\n"
            )

            print(response.output_text)

            return response.output_text

        # --------------------------------------------------
        # Add model output + tool results to conversation
        # --------------------------------------------------

        conversation.extend(response.output)

        conversation.extend(tool_outputs)

        # --------------------------------------------------
        # Ask model what to do next
        # --------------------------------------------------

        response = create_response(
            input_data=conversation,
        )

    # --------------------------------------------------
    # Maximum iterations reached
    # --------------------------------------------------

    print(
        "\n=== MAXIMUM ITERATIONS REACHED ==="
    )

    print(
        f"The agent stopped after "
        f"{MAX_AGENT_ITERATIONS} iterations."
    )

    if response.output_text:
        print("\nLast model response:")
        print(response.output_text)

    return response.output_text


# --------------------------------------------------
# Main
# --------------------------------------------------

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