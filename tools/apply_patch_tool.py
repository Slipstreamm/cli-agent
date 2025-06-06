import re
import os
from typing import Dict, Any, List, Optional
from .base_tool import BaseTool


class ApplyPatchTool(BaseTool):
    def get_name(self) -> str:
        return "apply_patch"

    def get_description(self) -> str:
        return "Apply changes to a file using find/replace. The 'find' operation can optionally use regular expressions. Supports a dry_run mode to preview changes."

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "file_path": "path/to/file",
            "changes": [
                {
                    "find": "text to find (can be a regex if use_regex is true)",
                    "replace": "replacement text",
                    "line_number": "Optional. Line number to apply the change to. If not provided, applies globally.",
                    "use_regex": "Optional. If true, the 'find' text will be treated as a regular expression. Defaults to false.",
                }
            ],
            "dry_run": "Optional. If true, simulates the changes without writing to the file. Defaults to false.",
        }

    def execute(
        self,
        file_path: str,
        changes: List[Dict[str, Any]],
        dry_run: bool = False,
        agent_safe_mode: bool = False,
        trace_id: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Apply a patch to a file using find/replace operations, with optional regex for find.
        Supports a dry_run mode to simulate changes without modifying the file.
        """
        # trace_id is available here if needed for logging within the tool
        try:
            if agent_safe_mode and os.path.exists(file_path) and not dry_run:
                confirm = input(
                    f"SAFE MODE: Confirm applying changes to '{file_path}'? [y/N]: "
                )
                if confirm.lower() not in ["y", "yes"]:
                    return {
                        "success": False,
                        "error": "Patch application not confirmed by user.",
                    }

            if not os.path.exists(file_path):
                return {"success": False, "error": f"File not found: {file_path}"}

            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            original_content = content
            lines = content.split("\n")
            changes_applied_details = []  # Renamed for clarity as per requirements

            for i, change in enumerate(changes):
                find_text = change.get("find", "")
                replace_text = change.get("replace", "")
                line_number = change.get("line_number")
                use_regex = change.get("use_regex", False)

                if not find_text:
                    changes_applied_details.append(
                        {
                            "change_index": i,
                            "success": False,
                            "error": "No 'find' text specified",
                        }
                    )
                    continue

                applied_this_change = False
                operation_type = "regex" if use_regex else "string"

                try:
                    if line_number is not None:
                        line_idx = line_number - 1
                        if 0 <= line_idx < len(lines):
                            original_line = lines[line_idx]
                            new_line_content = lines[
                                line_idx
                            ]  # Initialize with current line content

                            if use_regex:
                                new_line_content, num_replacements = re.subn(
                                    find_text, replace_text, new_line_content
                                )
                                if num_replacements > 0:
                                    lines[line_idx] = new_line_content
                                    applied_this_change = True
                            else:
                                if find_text in new_line_content:
                                    new_line_content = new_line_content.replace(
                                        find_text, replace_text
                                    )
                                    lines[line_idx] = new_line_content
                                    applied_this_change = True

                            if applied_this_change:
                                changes_applied_details.append(
                                    {
                                        "change_index": i,
                                        "success": True,
                                        "line_number": line_number,
                                        "original_line": original_line,
                                        "new_line": lines[line_idx],
                                        "operation": operation_type,
                                    }
                                )
                            else:
                                changes_applied_details.append(
                                    {
                                        "change_index": i,
                                        "success": False,
                                        "line_number": line_number,
                                        "error": f"{operation_type.capitalize()} pattern '{find_text}' not found on line {line_number}",
                                        "operation": operation_type,
                                    }
                                )
                        else:
                            changes_applied_details.append(
                                {
                                    "change_index": i,
                                    "success": False,
                                    "line_number": line_number,
                                    "error": f"Line number {line_number} is out of range (file has {len(lines)} lines)",
                                    "operation": operation_type,
                                }
                            )
                    else:  # Global replacement
                        # For global changes, we need to apply them to the 'content' string
                        # and then re-split into lines to keep 'lines' in sync.
                        # This ensures line numbers for subsequent line-specific changes are correct.
                        temp_content = "\n".join(
                            lines
                        )  # Use current state of lines for global search

                        if use_regex:
                            new_content, num_replacements = re.subn(
                                find_text, replace_text, temp_content
                            )
                            if num_replacements > 0:
                                lines = new_content.split(
                                    "\n"
                                )  # Update lines array after global regex change
                                changes_applied_details.append(
                                    {
                                        "change_index": i,
                                        "success": True,
                                        "occurrences_replaced": num_replacements,
                                        "global_replacement": True,
                                        "operation": operation_type,
                                    }
                                )
                                applied_this_change = True
                            else:
                                changes_applied_details.append(
                                    {
                                        "change_index": i,
                                        "success": False,
                                        "error": f"{operation_type.capitalize()} pattern '{find_text}' not found in file (global search)",
                                        "operation": operation_type,
                                    }
                                )
                        else:  # Simple string global replacement
                            if find_text in temp_content:
                                occurrences = temp_content.count(find_text)
                                new_content = temp_content.replace(
                                    find_text, replace_text
                                )
                                lines = new_content.split(
                                    "\n"
                                )  # Update lines array after global string change
                                changes_applied_details.append(
                                    {
                                        "change_index": i,
                                        "success": True,
                                        "occurrences_replaced": occurrences,
                                        "global_replacement": True,
                                        "operation": operation_type,
                                    }
                                )
                                applied_this_change = True
                            else:
                                changes_applied_details.append(
                                    {
                                        "change_index": i,
                                        "success": False,
                                        "error": f"Text '{find_text}' not found in file (global search)",
                                        "operation": operation_type,
                                    }
                                )
                except re.error as e_regex:
                    changes_applied_details.append(
                        {
                            "change_index": i,
                            "success": False,
                            "line_number": line_number,
                            "error": f"Invalid regex pattern '{find_text}': {str(e_regex)}",
                            "operation": "regex",
                        }
                    )
                except (
                    Exception
                ) as e_line:  # Catch other unexpected errors during change application
                    changes_applied_details.append(
                        {
                            "change_index": i,
                            "success": False,
                            "line_number": line_number,
                            "error": f"Error applying {operation_type} change: {str(e_line)}",
                            "operation": operation_type,
                        }
                    )

            modified_content = "\n".join(lines)

            file_was_modified = False
            if modified_content != original_content:
                if not dry_run:  # Only write if not in dry run mode
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(modified_content)
                    file_was_modified = True
                else:
                    file_was_modified = True  # In dry run, we consider it modified if changes would have occurred

            successful_individual_changes = sum(
                1 for chg_detail in changes_applied_details if chg_detail.get("success")
            )

            message_prefix = "Dry run: " if dry_run else ""
            message_suffix = " (no changes written to file)" if dry_run else ""

            return {
                "success": True,
                "message": f"{message_prefix}Processed {len(changes)} changes for {file_path}. {successful_individual_changes} individual changes would have been applied successfully{message_suffix}.",
                "changes_applied_details": changes_applied_details,
                "file_modified": file_was_modified,
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"An unexpected error occurred: {str(e)}",
            }
