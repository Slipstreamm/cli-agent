import re
from typing import Dict, Any, List, Optional

from .base_tool import BaseTool

class SearchFileContentTool(BaseTool):
    def get_name(self) -> str:
        return "search_file_content"

    def get_description(self) -> str:
        return "Search for a string or regex pattern within a single file. Returns a list of matching lines and their numbers."

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "file_path": "The path to the file to search within.",
            "query": "The string or regex pattern to search for.",
            "is_regex": "Optional. If true, the 'query' is treated as a regex pattern. Defaults to false.",
            "case_sensitive": "Optional. If true, the search is case-sensitive. Defaults to true."
        }

    def execute(self, file_path: str, query: str, is_regex: bool = False, case_sensitive: bool = True, agent_safe_mode: bool = False, trace_id: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        # trace_id is available here if needed for logging within the tool
        # This tool is not destructive.
        matches: List[Dict[str, Any]] = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except FileNotFoundError:
            return {"success": False, "error": f"File not found: {file_path}"}
        except Exception as e:
            return {"success": False, "error": f"Error reading file {file_path}: {str(e)}"}

        for line_num_0_based, line_content in enumerate(lines):
            line_text = line_content.rstrip('\n')
            line_number = line_num_0_based + 1

            if is_regex:
                try:
                    flags = re.IGNORECASE if not case_sensitive else 0
                    compiled_pattern = re.compile(query, flags)
                except re.error as e:
                    return {"success": False, "error": f"Invalid regex pattern: {str(e)}"}
                
                for match in compiled_pattern.finditer(line_text):
                    matches.append({
                        "line_number": line_number,
                        "line_text": line_text,
                        "match_segment": match.group(0),
                        "start_index": match.start(),
                        "end_index": match.end()
                    })
            else:  # Simple string search
                if not query: # Handle empty string query explicitly
                    # Matches at every position from 0 to len(line_text)
                    for i in range(len(line_text) + 1):
                        matches.append({
                            "line_number": line_number,
                            "line_text": line_text,
                            "match_segment": "", # query itself
                            "start_index": i,
                            "end_index": i
                        })
                else:
                    # Non-empty string query
                    temp_line_for_search = line_text
                    temp_query_for_search = query
                    if not case_sensitive:
                        temp_line_for_search = line_text.lower()
                        temp_query_for_search = query.lower()
                    
                    current_pos = 0
                    while current_pos < len(temp_line_for_search):
                        # If temp_query_for_search is empty, this loop is skipped due to 'if not query:' check above
                        found_pos = temp_line_for_search.find(temp_query_for_search, current_pos)
                        
                        if found_pos == -1:
                            break
                        
                        original_segment = line_text[found_pos : found_pos + len(query)]
                        matches.append({
                            "line_number": line_number,
                            "line_text": line_text,
                            "match_segment": original_segment,
                            "start_index": found_pos,
                            "end_index": found_pos + len(query)
                        })
                        current_pos = found_pos + len(temp_query_for_search) # Advance by length of query
        
        return {"success": True, "matches": matches}