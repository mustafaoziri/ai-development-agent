from pathlib import Path
import subprocess


PROJECT_ROOT = Path(__file__).resolve().parent.parent / "customer_app"


def _safe_path(relative_path: str) -> Path:
    """
    Prevent the agent from accessing files outside the project directory.
    """
    path = (PROJECT_ROOT / relative_path).resolve()

    if not str(path).startswith(str(PROJECT_ROOT.resolve())):
        raise ValueError("Access outside the project directory is not allowed.")

    return path


def list_files() -> str:
    """List all files inside the project directory."""

    if not PROJECT_ROOT.exists():
        return "Project directory does not exist."

    files = []

    for path in PROJECT_ROOT.rglob("*"):
        if path.is_file():
            files.append(str(path.relative_to(PROJECT_ROOT)))

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

    return file_path.read_text(encoding="utf-8")


def write_file(path: str, content: str) -> str:
    """Create or overwrite a file inside the project directory."""

    file_path = _safe_path(path)

    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")

    return f"Successfully wrote file: {path}"


def run_command(command: str) -> str:
    """
    Run a shell command inside the project directory.

    This is intentionally limited to the project environment.
    """

    result = subprocess.run(
        command,
        shell=True,
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=60
    )

    output = result.stdout

    if result.stderr:
        output += f"\nSTDERR:\n{result.stderr}"

    return output[:10000]