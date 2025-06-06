import os
import stat
from datetime import datetime
from typing import Dict, Any, Optional

from .base_tool import BaseTool


class GetFileMetadataTool(BaseTool):
    def get_name(self) -> str:
        return "get_file_metadata"

    def get_description(self) -> str:
        return "Get metadata for a specified file or directory (e.g., size, type, modification date)."

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The path to the file or directory.",
                }
            },
            "required": ["path"],
        }

    def execute(
        self,
        path: str,
        agent_safe_mode: bool = False,
        trace_id: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        # trace_id is available here if needed for logging within the tool
        # This tool is not destructive.
        if not os.path.exists(path):
            return {"success": True, "metadata": {"path": path, "exists": False}}

        try:
            stat_info = os.stat(path)
            file_type = "unknown"
            if os.path.isfile(path):
                file_type = "file"
            elif os.path.isdir(path):
                file_type = "directory"
            else:
                # This case should ideally not be reached if os.path.exists is true
                # and it's not a file or directory (e.g. broken symlink on some OS)
                file_type = "other"

            metadata = {
                "path": path,
                "exists": True,
                "type": file_type,
                "size_bytes": stat_info.st_size,
                "modified_at_iso8601": datetime.fromtimestamp(
                    stat_info.st_mtime
                ).isoformat(),
                "created_at_or_changed_at_iso8601": datetime.fromtimestamp(
                    stat_info.st_ctime
                ).isoformat(),
                "permissions_octal": oct(stat.S_IMODE(stat_info.st_mode)),
            }
            return {"success": True, "metadata": metadata}
        except PermissionError:
            return {"success": False, "error": f"Permission denied for path: {path}"}
        except Exception as e:
            return {
                "success": False,
                "error": f"An error occurred while accessing path {path}: {str(e)}",
            }
