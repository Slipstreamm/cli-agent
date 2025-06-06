import subprocess
from typing import Dict, Any, Optional
from .base_tool import BaseTool

class ExecuteCommandTool(BaseTool):
    def get_name(self) -> str:
        return "execute_command"

    def get_description(self) -> str:
        return "Run terminal/shell commands. Supports optional timeout_seconds and working_directory parameters."

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "command": "command to execute",
            "timeout_seconds": "Optional. Maximum time in seconds for the command to run. Defaults to 30 seconds if not provided.",
            "working_directory": "Optional. Path to the directory where the command should be executed. Defaults to the agent's current working directory if not provided."
        }

    def execute(self, command: str, timeout_seconds: Optional[int] = None, working_directory: Optional[str] = None, agent_safe_mode: bool = False, trace_id: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Execute a shell command."""
        # trace_id is available here if needed for logging within the tool
        if agent_safe_mode:
            confirm = input(f"SAFE MODE: Confirm execution of command: '{command}'? [y/N]: ")
            if confirm.lower() not in ['y', 'yes']:
                return {"success": False, "error": "Command execution not confirmed by user."}

        effective_timeout = timeout_seconds if timeout_seconds is not None else 30
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=effective_timeout,
                cwd=working_directory
            )
            return {
                "success": True,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": f"Command timed out after {effective_timeout} seconds"}
        except Exception as e:
            return {"success": False, "error": str(e)}