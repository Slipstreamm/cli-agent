import os
from typing import Dict, Any, Optional

from .base_tool import BaseTool
from backup_utils import create_backup


class CreateBackupTool(BaseTool):
    def get_name(self) -> str:
        return "create_backup"

    def get_description(self) -> str:
        return "Create a backup of a file using the configured extension and directory."

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {"file_path": "path/to/file"}

    def execute(
        self,
        file_path: str,
        agent_safe_mode: bool = False,
        trace_id: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        config = kwargs.get("config", {})
        backup_cfg = config.get("backup", {})
        backup_ext = backup_cfg.get("extension", ".bak")
        backup_dir = backup_cfg.get("directory")
        try:
            if not os.path.exists(file_path):
                return {"success": False, "error": f"File not found: {file_path}"}
            backup_path = create_backup(
                file_path, extension=backup_ext, backup_dir=backup_dir
            )
            return {"success": True, "message": f"Backup created at {backup_path}"}
        except Exception as exc:
            return {"success": False, "error": str(exc)}
