import os
from typing import Dict, Any, Optional
from .base_tool import BaseTool

class CreateDirectoryTool(BaseTool):
    def get_name(self) -> str:
        return "create_directory"

    def get_description(self) -> str:
        return "Create a new directory."

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {"directory_path": "path/to/new/directory"}

    def execute(self, directory_path: str, agent_safe_mode: bool = False, trace_id: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        # trace_id is available here if needed for logging within the tool
        try:
            # Safe mode check for directory creation
            if agent_safe_mode:
                user_confirmation = input(f"Safe Mode: Create directory '{directory_path}'? (yes/no): ").strip().lower()
                if user_confirmation != 'yes':
                    return {"success": False, "message": "Directory creation cancelled by user in safe mode."}
            
            os.makedirs(directory_path, exist_ok=True)
            return {"success": True, "message": f"Directory created: {directory_path}"}
        except Exception as e:
            return {"success": False, "error": str(e)}