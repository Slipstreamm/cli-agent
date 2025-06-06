import os
from typing import Dict, Any, Optional
from .base_tool import BaseTool

class DeleteFileTool(BaseTool):
    def get_name(self) -> str:
        return "delete_file"

    def get_description(self) -> str:
        return "Delete a file."

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {"file_path": "path/to/file"}

    def execute(self, file_path: str, agent_safe_mode: bool = False, trace_id: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        # trace_id is available here if needed for logging within the tool
        try:
            if agent_safe_mode:
                confirm = input(f"SAFE MODE: Confirm deletion of '{file_path}'? [y/N]: ")
                if confirm.lower() not in ['y', 'yes']:
                    return {"success": False, "error": "Deletion not confirmed by user."}
            os.remove(file_path)
            return {"success": True, "message": f"File deleted: {file_path}"}
        except Exception as e:
            return {"success": False, "error": str(e)}