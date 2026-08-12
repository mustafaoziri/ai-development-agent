from pathlib import Path
import subprocess
import re


PROJECT_ROOT = (
    Path(__file__).resolve().parent.parent
    / "customer_app"
)


# --------------------------------------------------
# Command security
# --------------------------------------------------

BLOCKED_COMMAND_PATTERNS = [
    # Linux destructive commands
    r"\brm\s+-rf\b",
    r"\brm\s+-r\b",

    # Windows destructive commands
    r"\bdel\s+/[a-z]*s[a-z]*\b",
    r"\brmdir\s+/[a-z]*s[a-z]*\b",

    # Disk / system destructive commands
    r"\bformat\b",
    r"\bdiskpart\b",
    r"\bshutdown\b",
    r"\breboot\b",

    # Registry
    r"\breg\s+(delete|add)\b",

    # PowerShell
    r"\bpowershell\b",

    # Command shell nesting
    r"\bcmd\s+/c\b",

    # Download / execution combinations
    r"\bcurl\b.*\|\s*(sh|bash)",
    r"\bwget\b.*\|\s*(sh|bash)",

    # Permission manipulation
    r"\bchmod\s+777\b",
]


def _validate_command(command: str):

    command = command.strip()

    if not command:
        raise ValueError(
            "Command cannot be empty."
        )

    # Prevent excessively large commands
    if len(command) > 2000:
        raise ValueError(
            "Command is too long."
        )

    command_lower = command.lower()

    for pattern in BLOCKED_COMMAND_PATTERNS:

        if re.search(
            pattern,
            command_lower,
        ):
            raise ValueError(
                "Command blocked for security reasons."
            )


def _safe_path(relative_path: str) -> Path:

    """
    Prevent the agent from accessing files
    outside the project directory.
    """

    path = (
        PROJECT_ROOT / relative_path
    ).resolve()

    if not str(path).startswith(
        str(PROJECT_ROOT.resolve())
    ):
        raise ValueError(
            "Access outside the project "
            "directory is not allowed."
        )

    return path


# --------------------------------------------------
# File tools
# --------------------------------------------------

def list_files() -> str:

    """List all files inside the project directory."""

    if not PROJECT_ROOT.exists():
        return (
            "Project directory does not exist."
        )

    files = []

    for path in PROJECT_ROOT.rglob("*"):

        if path.is_file():

            files.append(
                str(
                    path.relative_to(
                        PROJECT_ROOT
                    )
                )
            )

    if not files:
        return "No files found."

    return "\n".join(files)


def read_file(path: str) -> str:

    """Read a file from the project directory."""

    file_path = _safe_path(path)

    if not file_path.exists():
        return f"File not found: {path}"

    if not file_path.is_file():
        return f"{path} is not a file."

    return file_path.read_text(
        encoding="utf-8"
    )


def write_file(
    path: str,
    content: str,
) -> str:

    """Create or overwrite a file inside
    the project directory."""

    file_path = _safe_path(path)

    file_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    file_path.write_text(
        content,
        encoding="utf-8",
    )

    return (
        f"Successfully wrote file: {path}"
    )


# --------------------------------------------------
# Command tool
# --------------------------------------------------

def run_command(command: str) -> str:

    """
    Run a shell command inside the project directory.

    Commands are validated before execution.
    """

    _validate_command(command)

    if not PROJECT_ROOT.exists():
        PROJECT_ROOT.mkdir(
            parents=True,
            exist_ok=True,
        )

    try:

        result = subprocess.run(
            command,
            shell=True,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=60,
        )

    except subprocess.TimeoutExpired:

        return (
            "Command timed out after 60 seconds."
        )

    output = result.stdout

    if result.stderr:

        output += (
            "\nSTDERR:\n"
            + result.stderr
        )

    output += (
        f"\n\nExit code: {result.returncode}"
    )

    return output[:10000]