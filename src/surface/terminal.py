import subprocess

from src.agent.models import Observation, UIElement


class TerminalSurface:
    """Terminal adapter with an explicit executable allowlist and no shell."""

    def __init__(self, allowed_commands=None, timeout_seconds=10):
        self.allowed_commands = set(allowed_commands or {"python", "python3", "git"})
        self.timeout_seconds = timeout_seconds
        self.command = None
        self.output = ""

    def start(self):
        return self

    def navigate(self, target):
        self.command = target

    def observe(self):
        return Observation(
            url=f"terminal://{self.command or 'idle'}",
            title="Restricted Terminal",
            text=self.output,
            elements=[
                UIElement(
                    element_id="e1",
                    role="textbox",
                    name="Command Arguments",
                    selector="terminal.arguments",
                    value="",
                )
            ],
        )

    def execute_command(self, argv):
        if not argv or argv[0] not in self.allowed_commands:
            raise ValueError("Executable is not allowlisted.")
        completed = subprocess.run(
            argv,
            shell=False,
            capture_output=True,
            text=True,
            timeout=self.timeout_seconds,
            check=False,
        )
        self.output = (completed.stdout + completed.stderr)[:8000]
        return completed.returncode

    def execute(self, action, observation):
        raise NotImplementedError(
            "Terminal actions must be compiled to an argv capability and "
            "approved before execute_command; arbitrary LLM commands are disabled."
        )

    def wait(self, milliseconds=1000):
        return None

    def screenshot(self, path):
        return None

    def close(self):
        return None
