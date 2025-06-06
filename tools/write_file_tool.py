import os
from typing import Dict, Any, Optional
from .base_tool import BaseTool

class WriteFileTool(BaseTool):
    def get_name(self) -> str:
        return "write_file"

    def get_description(self) -> str:
        return "Write content to a file. Optionally, specify the file encoding."

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "file_path": "path/to/file",
            "content": "text content",
            "mode": "w or a",
            "encoding": "Optional. The file encoding to use (e.g., 'utf-8', 'ascii'). Defaults to 'utf-8'."
        }

    def execute(self, file_path: str, content: str, mode: str = "w", encoding: Optional[str] = 'utf-8', agent_safe_mode: bool = False, trace_id: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Write content to a file."""
        # trace_id is available here if needed for logging within the tool
        try:
            if agent_safe_mode and mode == 'w' and os.path.exists(file_path):
                confirm = input(f"SAFE MODE: Confirm overwrite of '{file_path}'? [y/N]: ")
                if confirm.lower() not in ['y', 'yes']:
                    return {"success": False, "error": "Overwrite not confirmed by user."}

            # Use a default encoding if None is provided, though the signature defaults to 'utf-8'
            effective_encoding = encoding if encoding is not None else 'utf-8'
            with open(file_path, mode, encoding=effective_encoding) as f:
                f.write(content)
            return {"success": True, "message": f"Content written to {file_path} with encoding {effective_encoding}"}
        except Exception as e:
            return {"success": False, "error": str(e)}