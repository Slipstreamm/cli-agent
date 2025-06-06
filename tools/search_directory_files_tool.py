import os
import re
import fnmatch
from typing import Dict, Any, List, Optional

from .base_tool import BaseTool


class SearchDirectoryFilesTool(BaseTool):
    """
    Tool to recursively search for a string or regex pattern in files within a directory.
    """

    def get_name(self) -> str:
        """Returns the name of the tool."""
        return "search_directory_files"

    def get_description(self) -> str:
        """Returns a description of the tool."""
        return (
            "Recursively search for a string or regex pattern in files within a directory. "
            "Returns a list of files containing matches and the count of matches per file."
        )

    def get_parameters_schema(self) -> Dict[str, Any]:
        """Returns the schema for the tool's parameters."""
        return {
            "type": "object",
            "properties": {
                "directory_path": {
                    "type": "string",
                    "description": "The path to the directory to search within.",
                },
                "query": {
                    "type": "string",
                    "description": "The string or regex pattern to search for.",
                },
                "is_regex": {
                    "type": "boolean",
                    "description": "Optional. If true, the 'query' is treated as a regex pattern. Defaults to false.",
                    "default": False,
                },
                "case_sensitive": {
                    "type": "boolean",
                    "description": "Optional. If true, the search is case-sensitive. Defaults to true.",
                    "default": True,
                },
                "glob_pattern": {
                    "type": "string",
                    "description": "Optional. A glob pattern (e.g., '*.py', '*.txt') to filter which files are searched. Defaults to '*' (all files).",
                    "default": "*",
                },
                "recursive": {
                    "type": "boolean",
                    "description": "Optional. If true, searches recursively into subdirectories. Defaults to true.",
                    "default": True,
                },
            },
            "required": ["directory_path", "query"],
        }

    def execute(
        self,
        directory_path: str,
        query: str,
        is_regex: bool = False,
        case_sensitive: bool = True,
        glob_pattern: str = "*",
        recursive: bool = True,
        agent_safe_mode: bool = False,  # Added for consistency, though not used by this non-destructive tool
        trace_id: Optional[str] = None,  # Added trace_id
        **kwargs: Any,  # pylint: disable=unused-argument
    ) -> Dict[str, Any]:
        """
        Executes the search operation.
        # trace_id is available here if needed for logging within the tool

        Args:
            directory_path: The path to the directory to search within.
            query: The string or regex pattern to search for.
            is_regex: If true, 'query' is a regex. Defaults to False.
            case_sensitive: If true, search is case-sensitive. Defaults to True.
            glob_pattern: Glob pattern to filter files. Defaults to "*".
            recursive: If true, searches recursively. Defaults to True.
            kwargs: Additional keyword arguments.

        Returns:
            A dictionary with the search results or an error message.
        """
        if not os.path.isdir(directory_path):
            return {"success": False, "error": f"Directory not found: {directory_path}"}

        found_files_info: List[Dict[str, Any]] = []

        compiled_pattern = None
        if is_regex:
            try:
                flags = 0 if case_sensitive else re.IGNORECASE
                compiled_pattern = re.compile(query, flags)
            except re.error as e:
                return {"success": False, "error": f"Invalid regex pattern: {str(e)}"}

        for root, dirs, files_in_dir in os.walk(directory_path, topdown=True):
            if not recursive:
                dirs[:] = []  # Don't go into subdirectories if not recursive

            for filename in files_in_dir:
                if fnmatch.fnmatch(filename, glob_pattern):
                    file_path = os.path.join(root, filename)
                    matches_count = 0
                    try:
                        # Try to open as text, ignore errors for binary files or encoding issues
                        with open(
                            file_path, "r", encoding="utf-8", errors="ignore"
                        ) as f:
                            content = f.read()
                            if compiled_pattern:  # Regex search
                                matches_count = len(compiled_pattern.findall(content))
                            else:  # Simple string search
                                if case_sensitive:
                                    matches_count = content.count(query)
                                else:
                                    matches_count = content.lower().count(query.lower())

                        if matches_count > 0:
                            found_files_info.append(
                                {"file_path": file_path, "matches_count": matches_count}
                            )
                    except OSError:
                        # Could be a directory masquerading as a file, or permission error, etc.
                        # Skip this file.
                        pass
                    except Exception:
                        # Catch other potential errors during file processing (e.g. rare Unicode issues not caught by 'ignore')
                        # Skip this file.
                        pass

            # If not recursive, and we've processed the top-level directory, we can stop.
            # The `dirs[:] = []` handles this by preventing os.walk from yielding subdirectories.
            # However, if directory_path itself has no subdirectories, os.walk will naturally stop.
            # If directory_path has subdirectories, `dirs[:] = []` ensures they are not traversed.
            # This logic is fine.

        return {"success": True, "found_files": found_files_info}
