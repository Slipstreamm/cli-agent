from typing import Dict, Any, Optional

from .base_tool import BaseTool
from backup_utils import restore_backups


class RestoreBackupsTool(BaseTool):
    def get_name(self) -> str:
        return "restore_backups"

    def get_description(self) -> str:
        return "Restore backups from the configured directory and extension."

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {}

    def execute(
        self,
        agent_safe_mode: bool = False,
        trace_id: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        config = kwargs.get("config", {})
        backup_cfg = config.get("backup", {})
        backup_ext = backup_cfg.get("extension", ".bak")
        backup_dir = backup_cfg.get("directory") or "."
        try:
            restore_backups(
                search_dir=backup_dir, extension=backup_ext, target_root="."
            )
            return {"success": True, "message": "Backups restored"}
        except Exception as exc:
            return {"success": False, "error": str(exc)}
