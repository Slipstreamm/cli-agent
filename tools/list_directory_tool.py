import os
import fnmatch
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from .base_tool import BaseTool

class ListDirectoryTool(BaseTool):
    def get_name(self) -> str:
        return "list_directory"

    def get_description(self) -> str:
        return "List contents of a directory. Supports recursive listing, glob pattern filtering, and inclusion of file metadata."

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "directory_path": "Optional. path/to/directory. Defaults to '.' (current directory).",
            "recursive": "Optional. If true, lists directory contents recursively. Defaults to false.",
            "glob_pattern": "Optional. A glob pattern (e.g., '*.py', 'data*') to filter items. Defaults to '*' (all items).",
            "include_metadata": "Optional. If true, includes basic metadata (type, size, modified_at) for each item. Defaults to false."
        }

    def execute(self, directory_path: str = ".", recursive: bool = False, glob_pattern: str = "*", include_metadata: bool = False, agent_safe_mode: bool = False, trace_id: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        # trace_id is available here if needed for logging within the tool
        try:
            # This tool is not destructive.
            results: List[Union[str, Dict[str, Any]]] = []
            if recursive:
                for root, dirs, files in os.walk(directory_path):
                    # Filter directories
                    matched_dirs = [d for d in dirs if fnmatch.fnmatch(d, glob_pattern)]
                    for name in matched_dirs:
                        item_path = os.path.join(root, name)
                        if include_metadata:
                            try:
                                stat_info = os.stat(item_path)
                                results.append({
                                    "name": name,
                                    "path": item_path,
                                    "type": "directory",
                                    "size_bytes": 0, # Or stat_info.st_size if meaningful for dirs
                                    "modified_at": datetime.fromtimestamp(stat_info.st_mtime).isoformat()
                                })
                            except OSError: # Handle cases like permission denied for stat
                                results.append({
                                    "name": name,
                                    "path": item_path,
                                    "type": "directory",
                                    "error": "Could not retrieve metadata"
                                })
                        else:
                            results.append(item_path)
                    dirs[:] = matched_dirs # Prune dirs for os.walk to only visit matched ones if pattern doesn't include wildcards for path components

                    # Filter files
                    for name in files:
                        if fnmatch.fnmatch(name, glob_pattern):
                            item_path = os.path.join(root, name)
                            if include_metadata:
                                try:
                                    stat_info = os.stat(item_path)
                                    results.append({
                                        "name": name,
                                        "path": item_path,
                                        "type": "file",
                                        "size_bytes": stat_info.st_size,
                                        "modified_at": datetime.fromtimestamp(stat_info.st_mtime).isoformat()
                                    })
                                except OSError:
                                    results.append({
                                        "name": name,
                                        "path": item_path,
                                        "type": "file",
                                        "error": "Could not retrieve metadata"
                                    })
                            else:
                                results.append(item_path)
            else:
                for item_name in os.listdir(directory_path):
                    if fnmatch.fnmatch(item_name, glob_pattern):
                        item_path = os.path.join(directory_path, item_name)
                        if include_metadata:
                            try:
                                stat_info = os.stat(item_path)
                                is_dir = os.path.isdir(item_path)
                                results.append({
                                    "name": item_name,
                                    "path": item_path,
                                    "type": "directory" if is_dir else "file",
                                    "size_bytes": stat_info.st_size if not is_dir else 0,
                                    "modified_at": datetime.fromtimestamp(stat_info.st_mtime).isoformat()
                                })
                            except OSError:
                                results.append({
                                    "name": item_name,
                                    "path": item_path,
                                    "type": "directory" if os.path.isdir(item_path) else "file",
                                    "error": "Could not retrieve metadata"
                                })
                        else:
                            results.append(item_path if recursive else item_name) # if not recursive, just name

            return {"success": True, "items": results}
        except Exception as e:
            return {"success": False, "error": str(e)}