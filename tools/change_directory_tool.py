import os
from typing import Dict, Any, Optional
from .base_tool import BaseTool

class ChangeDirectoryTool(BaseTool):
    def get_name(self) -> str:
        return "change_directory"

    def get_description(self) -> str:
        return "Change current working directory."

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {"directory_path": "path/to/directory"}

    def execute(self, directory_path: str, agent_safe_mode: bool = False, trace_id: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        # trace_id is available here if needed for logging within the tool
        try:
            # This tool is not inherently destructive, but changing directory might be part of a
            # sequence that leads to destructive actions. However, per current requirements,
            # only specified tools get the confirmation prompt.
            # If safe mode were to gate *all* filesystem operations, this would need a check.
            os.chdir(directory_path)
            new_cwd = os.getcwd()
            return {"success": True, "message": f"Changed to directory: {new_cwd}"}
        except Exception as e:
            return {"success": False, "error": str(e)}