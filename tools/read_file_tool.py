from typing import Dict, Any, Optional
from .base_tool import BaseTool


class ReadFileTool(BaseTool):
    def get_name(self) -> str:
        return "read_file"

    def get_description(self) -> str:
        return "Read contents of a file. Supports specifying encoding, start line, and end line."

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "file_path": "path/to/file",
            "encoding": "Optional. The file encoding to use (e.g., 'utf-8', 'ascii'). Defaults to 'utf-8'.",
            "start_line": "Optional. The 1-based line number to start reading from. Reads from the beginning if not specified.",
            "end_line": "Optional. The 1-based line number to stop reading at (inclusive). Reads to the end if not specified.",
        }

    def execute(
        self,
        file_path: str,
        encoding: Optional[str] = "utf-8",
        start_line: Optional[int] = None,
        end_line: Optional[int] = None,
        agent_safe_mode: bool = False,
        trace_id: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Read contents of a file, with optional encoding and line range."""
        # trace_id is available here if needed for logging within the tool
        try:
            # This tool is not destructive.
            with open(file_path, "r", encoding=encoding or "utf-8") as f:
                if start_line is None and end_line is None:
                    content = f.read()
                else:
                    lines = f.readlines()
                    # Adjust for 0-based indexing if start_line is provided
                    start_index = (start_line - 1) if start_line is not None else 0
                    # end_line is inclusive, so no adjustment needed for slicing if end_line is provided
                    # If end_line is None, read till the end of the file
                    end_index = end_line if end_line is not None else len(lines)

                    # Ensure indices are within bounds
                    start_index = max(0, start_index)
                    end_index = min(len(lines), end_index)

                    if (
                        start_index >= end_index
                    ):  # Handles cases where start_line is beyond file length or start > end
                        content = ""
                    else:
                        content = "".join(lines[start_index:end_index])
            return {"success": True, "content": content}
        except FileNotFoundError:
            return {"success": False, "error": f"File not found: {file_path}"}
        except LookupError:  # Handles unknown encoding
            return {"success": False, "error": f"Unknown encoding: {encoding}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
