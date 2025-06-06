import requests
import json
from typing import Dict, Any, Optional

from .base_tool import BaseTool


class HttpRequestTool(BaseTool):
    """
    A tool to perform HTTP requests.
    """

    def get_name(self) -> str:
        """
        Returns the name of the tool.
        """
        return "http_request"

    def get_description(self) -> str:
        """
        Returns a description of the tool.
        """
        return "Perform an HTTP request to a specified URL. Supports GET, POST, PUT, DELETE methods and custom headers/body."

    def get_parameters_schema(self) -> Dict[str, Any]:
        """
        Returns the schema for the tool's parameters.
        """
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL to make the request to.",
                },
                "method": {
                    "type": "string",
                    "description": "Optional. The HTTP method to use (GET, POST, PUT, DELETE, etc.). Defaults to GET.",
                },
                "headers": {
                    "type": "object",
                    "description": "Optional. A dictionary of HTTP headers to send.",
                    "additionalProperties": {"type": "string"},
                },
                "json_body": {
                    "type": "object",
                    "description": "Optional. A JSON serializable dictionary to send as the request body (for POST, PUT, etc.). If provided, 'Content-Type: application/json' header will be added automatically if not present.",
                },
                "data_body": {
                    "type": "string",
                    "description": "Optional. A string to send as the raw request body. Use this for non-JSON bodies.",
                },
                "timeout_seconds": {
                    "type": "integer",
                    "description": "Optional. Maximum time in seconds to wait for a response. Defaults to 10 seconds.",
                },
            },
            "required": ["url"],
        }

    def execute(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        json_body: Optional[Dict[str, Any]] = None,
        data_body: Optional[str] = None,
        timeout_seconds: int = 10,
        agent_safe_mode: bool = False,
        trace_id: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Executes the HTTP request.
        """
        # trace_id is available here if needed for logging within the tool
        # This tool is not destructive in the sense of local file system changes.
        # Confirmation for HTTP requests might be desired in some contexts (e.g., POST to sensitive endpoints),
        # but it's not part of the current "destructive actions" scope focused on local files/commands.
        if headers is None:
            headers = {}

        effective_method = method.upper()

        if json_body is not None:
            if not any(h.lower() == "content-type" for h in headers):
                headers["Content-Type"] = "application/json"

        try:
            response = requests.request(
                method=effective_method,
                url=url,
                headers=headers,
                json=json_body,
                data=data_body,
                timeout=timeout_seconds,
            )

            response_json_content: Optional[Dict[str, Any]] = None
            content_type = response.headers.get("Content-Type", "")
            if "application/json" in content_type:
                try:
                    response_json_content = response.json()
                except json.JSONDecodeError:
                    pass

            if response.status_code >= 400:
                return {
                    "success": False,
                    "error": f"HTTP Error: {response.status_code} - {response.reason}",
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "response_json": response_json_content,
                    "response_text": response.text,
                }

            return {
                "success": True,
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "response_json": response_json_content,
                "response_text": response.text,
            }

        except requests.exceptions.Timeout:
            return {"success": False, "error": "Timeout occurred", "status_code": None}
        except requests.exceptions.ConnectionError as e:
            return {
                "success": False,
                "error": f"Connection error: {e}",
                "status_code": None,
            }
        except requests.exceptions.RequestException as e:
            status_code = e.response.status_code if e.response is not None else None
            return {
                "success": False,
                "error": f"Request failed: {e}",
                "status_code": status_code,
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"An unexpected error occurred: {str(e)}",
                "status_code": None,
            }
