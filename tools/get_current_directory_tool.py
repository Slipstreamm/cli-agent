import os
from typing import Dict, Any, Optional
from .base_tool import BaseTool


class GetCurrentDirectoryTool(BaseTool):
    def get_name(self) -> str:
        return "get_current_directory"

    def get_description(self) -> str:
        return "Get current working directory."

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {}  # No parameters

    def execute(
        self, agent_safe_mode: bool = False, trace_id: Optional[str] = None, **kwargs
    ) -> Dict[str, Any]:
        # trace_id is available here if needed for logging within the tool
        try:
            cwd = os.getcwd()
            return {"success": True, "current_directory": cwd}
        except Exception as e:
            return {"success": False, "error": str(e)}
