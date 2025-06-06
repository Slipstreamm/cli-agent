import subprocess
from typing import Dict, Any, Optional
from tools.base_tool import BaseTool

class GitTool(BaseTool):
    """
    A tool to execute basic Git commands.
    """

    def get_name(self) -> str:
        """
        Returns the callable name of the tool.
        """
        return "git_tool"

    def get_description(self) -> str:
        """
        Returns a description of the tool for the LLM.
        Warns about security implications of executing arbitrary commands.
        """
        return (
            "Executes basic Git commands. "
            "WARNING: The 'command' input is directly passed to subprocess.run with shell=True. "
            "Ensure the input is trusted to avoid potential security vulnerabilities."
        )

    def get_parameters_schema(self) -> Dict[str, Any]:
        """
        Returns a dictionary representing the simplified schema of parameters for the GitTool.
        """
        return {
            "command": {
                "type": "string",
                "description": "The Git command to execute (e.g., 'status', 'add .', 'commit -m \"message\"')."
            }
        }

    def execute(self, command: str, agent_safe_mode: bool = False, trace_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Executes the given Git command using subprocess.run.

        Args:
            command (str): The Git command to execute.
            agent_safe_mode (bool): Indicates if the agent is in safe mode (not used by this tool).
            trace_id (Optional[str]): An optional trace ID for logging/tracking (not used by this tool).

        Returns:
            Dict[str, Any]: A dictionary containing the result of the Git command execution.
                            Includes success status, command, stdout, stderr, return code, and error message.
        """
        try:
            # Execute the Git command
            result = subprocess.run(
                f"git {command}",
                shell=True,
                capture_output=True,
                text=True,
                check=False  # Do not raise an exception for non-zero exit codes
            )

            success = result.returncode == 0
            error_message = None
            if not success and result.stderr:
                error_message = result.stderr.strip()

            return {
                "success": success,
                "command": command,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
                "return_code": result.returncode,
                "error_message": error_message
            }
        except Exception as e:
            return {
                "success": False,
                "command": command,
                "stdout": "",
                "stderr": str(e),
                "return_code": 1,  # Indicate an error
                "error_message": str(e)
            }