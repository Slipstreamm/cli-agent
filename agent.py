import json
import os
import subprocess
import re
import sys
import argparse
import time # Added for retries
import importlib
import pkgutil
import inspect
import yaml # Added for config file
import logging # Added for logging
import uuid # Added for trace IDs
from typing import Dict, Any, List, Optional, Iterable, Tuple, MutableMapping

from google.cloud import aiplatform
from vertexai.generative_models import GenerativeModel, Part  # type: ignore
from google.cloud.aiplatform_v1beta1.types import GenerateContentResponse
import vertexai # type: ignore
from google.api_core import exceptions as google_api_exceptions # Added for specific API error handling

from tools.base_tool import BaseTool

DEFAULT_CONFIG_PATH = "config.yaml"

def load_config(config_path: str = DEFAULT_CONFIG_PATH) -> Dict[str, Any]:
    """Loads configuration from a YAML file."""
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        if config is None: # Handle empty config file
            return {}
        return config
    except FileNotFoundError:
        print(f"Warning: Configuration file '{config_path}' not found. Using default values.")
        return {}
    except yaml.YAMLError as e:
        print(f"Error parsing configuration file '{config_path}': {e}")
        return {} # Or raise an error, or return a default config structure

# Custom LoggerAdapter to inject trace_id
class TraceIdAdapter(logging.LoggerAdapter):
    def process(self, msg: str, kwargs: MutableMapping[str, Any]) -> Tuple[str, MutableMapping[str, Any]]:
        if 'trace_id' not in self.extra:
            self.extra['trace_id'] = None # Default if not set
        # Ensure trace_id from extra is preferred if not explicitly passed in kwargs
        # kwargs.setdefault('extra', {}) # Ensure 'extra' key exists in kwargs
        # if 'trace_id' not in kwargs['extra']: # type: ignore
        #    kwargs['extra']['trace_id'] = self.extra.get('trace_id') # type: ignore
        
        # The default LoggerAdapter.process will handle merging 'extra' from kwargs
        # with self.extra. We just need to ensure our self.extra['trace_id'] is available.
        return msg, kwargs

def setup_logging(config: Dict[str, Any], verbose_cli: bool = False):
    """Configures logging based on the provided configuration and verbose flag."""
    log_config = config.get("logging", {})
    
    # Determine log level: CLI verbose flag takes precedence for console.
    if verbose_cli:
        level_name = "DEBUG"
    else:
        level_name = log_config.get("default_level", "INFO").upper()
    
    log_level = getattr(logging, level_name, logging.INFO)
    
    log_to_file = log_config.get("log_to_file", False)
    log_file_path = log_config.get("log_file_path", "agent.log")

    # Formatter with trace_id
    log_format = '%(asctime)s - %(levelname)s - %(name)s - [%(trace_id)s] - %(message)s'
    formatter = logging.Formatter(log_format)

    # Remove all handlers associated with the root logger object.
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    
    # Configure root logger
    logging.getLogger().setLevel(min(log_level, logging.DEBUG if log_to_file else log_level)) # Ensure root can pass all messages to handlers

    # Console Handler (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level) # Level determined by verbose_cli or config
    logging.getLogger().addHandler(console_handler)

    if log_to_file:
        try:
            log_dir = os.path.dirname(log_file_path)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)

            file_handler = logging.FileHandler(log_file_path, mode='a')
            file_handler.setFormatter(formatter)
            # File logger level can be more verbose if desired, e.g., always DEBUG
            file_handler_level_name = log_config.get("file_log_level", "DEBUG").upper()
            file_handler_level = getattr(logging, file_handler_level_name, logging.DEBUG)
            file_handler.setLevel(file_handler_level)
            
            logging.getLogger().addHandler(file_handler)
            # Use a basic logger here as our adapter isn't set up globally yet
            logging.info(f"Logging to file: {log_file_path} at level {file_handler_level_name}")
        except Exception as e:
            logging.error(f"Failed to set up file logger at {log_file_path}: {e}", exc_info=True)

class VertexAIAgent:
    def __init__(self, project_id: str, location: str, model_name: str, api_retry_config: Dict[str, Any], safe_mode: bool, config: Dict[str, Any]):
        """
        Initialize the Vertex AI Agent with custom tool calling capabilities.

        Args:
            project_id: Your Google Cloud Project ID
            location: GCP region
            model_name: Vertex AI model to use
            api_retry_config: Dictionary with API retry parameters
            safe_mode: Boolean indicating if safe mode is enabled
            config: The loaded application configuration
        """
        # Initialize logger first
        # The 'extra' dict will be used to store trace_id per task
        self.logger = TraceIdAdapter(logging.getLogger(__name__), {'trace_id': None})
        self.config = config # Store the config

        self.project_id = project_id
        self.location = location
        self.model_name = model_name
        self.api_retry_config = api_retry_config
        self.safe_mode = safe_mode

        # Initialize Vertex AI
        # vertexai.init(project=project_id, location=location) # This might be called multiple times if agent is re-initialized.
                                                            # Consider if it should be called once globally.
                                                            # For now, keeping original behavior.
        try:
            vertexai.init(project=project_id, location=location)
            self.logger.info(f"Vertex AI initialized for project '{project_id}' in location '{location}'.")
        except Exception as e:
            self.logger.error(f"Failed to initialize Vertex AI: {e}", exc_info=True)
            # Depending on severity, might want to raise this or handle gracefully.
            # For now, logging and continuing.
            pass # Or raise e

        self.model = GenerativeModel(model_name)
        self.logger.info(f"Using model: {model_name}")

        # Instantiate and store tool instances
        self.tool_instances: Dict[str, BaseTool] = self._load_tools() # _load_tools will use self.logger
        self.system_prompt = self._build_system_prompt()
        self.logger.debug("VertexAIAgent initialized.")

    def _load_tools(self) -> Dict[str, BaseTool]:
        """Dynamically loads tool classes from the 'tools' subdirectory."""
        loaded_tools: Dict[str, BaseTool] = {}
        tools_package_path = os.path.join(os.path.dirname(__file__), "tools")
        
        # Ensure the 'tools' directory is treated as a package
        # This might involve adjusting sys.path or ensuring tools_package_path is discoverable
        # For simplicity, we assume 'tools' is a sibling directory and importable.
        
        for (_, module_name, _) in pkgutil.iter_modules([tools_package_path]):
            if module_name == "__init__" or module_name == "base_tool":
                continue # Skip __init__.py and base_tool.py itself
            try:
                module = importlib.import_module(f"tools.{module_name}")
                for attribute_name, attribute_value in inspect.getmembers(module):
                    if inspect.isclass(attribute_value) and \
                       issubclass(attribute_value, BaseTool) and \
                       attribute_value is not BaseTool:
                        try:
                            tool_instance = attribute_value()
                            loaded_tools[tool_instance.get_name()] = tool_instance
                            # self.project_id check is no longer relevant for logging verbosity here
                            self.logger.info(f"Successfully loaded tool: {tool_instance.get_name()} from {module_name}")
                        except Exception as e:
                            self.logger.error(f"Error instantiating tool {attribute_name} from {module_name}: {e}", exc_info=True)

            except ImportError as e:
                self.logger.error(f"Error importing module tools.{module_name}: {e}", exc_info=True)
            except Exception as e:
                self.logger.error(f"An unexpected error occurred while loading tools from {module_name}: {e}", exc_info=True)
        
        if not loaded_tools:
            self.logger.warning("No tools were loaded. Check the 'tools' directory and tool implementations.")
        else:
            self.logger.info(f"Loaded {len(loaded_tools)} tools: {', '.join(loaded_tools.keys())}")
        return loaded_tools

    def _get_response_text(self, response) -> str:
        """
        Extract text from Vertex AI response (or a chunk of it).
        This method is designed to be robust for both full responses and stream chunks.
        """
        try:
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'content') and candidate.content:
                    content = candidate.content
                    if hasattr(content, 'parts') and content.parts:
                        text_parts = []
                        for part in content.parts:
                            if hasattr(part, 'text') and part.text:
                                text_parts.append(part.text)
                        if text_parts:
                            return ''.join(text_parts)
        except Exception: 
            pass

        try:
            if hasattr(response, 'text') and response.text:
                return response.text
        except Exception:
            pass
        return ""

    def _build_system_prompt(self) -> str:
        """Build the system prompt that teaches the model how to use tools."""
        base_prompt = """You are a highly capable AI agent that accomplishes tasks by executing tools. Your primary directive is to base your actions and conclusions *exclusively* on the real-world feedback you receive from these tools. The tool's output is the absolute ground truth.

Your internal knowledge is only for creating hypotheses and plans. The tool results are for testing and confirming those plans. If a tool's output contradicts your belief, your belief is wrong.

**Workflow:**
1.  **Analyze the task:** Break down the request into a sequence of verifiable steps.
2.  **Formulate a step and call a tool:** Announce what you are about to do and why, then call the appropriate tool.
3.  **Analyze the result:** Treat the tool's JSON output as the absolute truth.
4.  **Report and revise:** Explain the outcome based on the tool's result. If the step failed, you MUST explain the error using the tool's feedback and formulate a new plan to overcome it. Do not proceed with a broken plan.

**Tool Calling Format:**
When you need to use a tool, format your call as follows:
<tool_call>
{
    "tool": "tool_name",
    "parameters": {
        "param1": "value1",
        "param2": "value2"
    }
}
</tool_call>

---

**ANALYZING TOOL RESULTS - THIS IS YOUR MOST IMPORTANT INSTRUCTION**

The output of a tool, especially `execute_command`, is your only source of truth.

-   **For `execute_command`:**
    -   A `"return_code": 0` means the command succeeded.
    -   A non-zero `"return_code"` means the command FAILED.
    -   The `"stderr"` field contains the error message explaining WHY it failed.
    -   If the `return_code` is not 0, you MUST stop, analyze the `stderr` content, and change your plan. Do not assume success. For example, if you see "command not found," your next step must be to find a way to install it or use a different command.

-   **For all other tools:**
    -   Look for a `"success": false` field and an `"error"` field. If a tool reports an error, you must address it.

---

**Available Tools:**
"""
        tool_descriptions = []
        for i, (name, tool_instance) in enumerate(self.tool_instances.items()):
            desc = f"{i+1}. **{tool_instance.get_name()}**: {tool_instance.get_description()}\n"
            params_schema = tool_instance.get_parameters_schema()
            if params_schema: # Ensure there are parameters to describe
                 desc += f"    * **Parameters**: `{json.dumps(params_schema)}`\n"
            else: # Handle tools with no parameters
                 desc += f"    * **Parameters**: `{{}}`\n"

            if tool_instance.get_name() == "execute_command":
                desc += "    * **Crucial Note**: ALWAYS check the `return_code` and `stderr` fields in the result. A non-zero `return_code` indicates failure.\n"
            tool_descriptions.append(desc)

        system_prompt = base_prompt + "\n" + "\n".join(tool_descriptions)
        system_prompt += "\n**Best Practice:** Before performing system-altering operations like installing software, it is often wise to first identify the operating system (e.g., by reading `/etc/os-release` or using `uname -a`) to ensure you use the correct commands.\n"
        return system_prompt

    def _extract_tool_calls(self, text: str) -> List[Dict[str, Any]]:
        tool_calls = []
        pattern = r'<tool_call>\s*(\{[\s\S]*?\})\s*</tool_call>'
        matches = re.findall(pattern, text, re.DOTALL)
        for match in matches:
            try:
                clean_match = match.strip()
                tool_call = json.loads(clean_match)
                tool_calls.append(tool_call)
            except json.JSONDecodeError as e:
                self.logger.error(f"Error parsing tool call JSON: {e}. Problematic string: '{match}'", exc_info=True)
        return tool_calls

    def _execute_tool_call(self, tool_call: Dict[str, Any], trace_id: Optional[str]) -> Dict[str, Any]:
        tool_name = tool_call.get("tool")
        parameters = tool_call.get("parameters", {})
        self.logger.debug(f"Executing tool: {tool_name} with params: {parameters}")

        if tool_name not in self.tool_instances:
            self.logger.error(f"Unknown tool called: {tool_name}")
            return {"success": False, "error": f"Unknown tool: {tool_name}"}
        
        tool_instance = self.tool_instances[tool_name]
        try:
            # Pass trace_id to the tool's execute method
            if not tool_instance.get_parameters_schema() and not parameters:
                 return tool_instance.execute(agent_safe_mode=self.safe_mode, trace_id=trace_id)
            return tool_instance.execute(**parameters, agent_safe_mode=self.safe_mode, trace_id=trace_id)
        except TypeError as te:
            param_schema = tool_instance.get_parameters_schema()
            error_msg = f"Tool execution error for '{tool_name}': Invalid or missing parameters. Expected: {param_schema}. Received: {parameters}. Details: {str(te)}"
            self.logger.error(error_msg, exc_info=True)
            return {"success": False, "error": error_msg}
        except Exception as e:
            self.logger.error(f"Tool execution error for '{tool_name}': {str(e)}", exc_info=True)
            return {"success": False, "error": f"Tool execution error for '{tool_name}': {str(e)}"}

    def _process_response(self, response_text: str, trace_id: Optional[str]) -> tuple[str, List[Dict[str, Any]]]:
        tool_calls = self._extract_tool_calls(response_text)
        tool_results = []
        if tool_calls:
            self.logger.info(f"Detected {len(tool_calls)} tool_call(s).")
        for tool_call in tool_calls:
            result = self._execute_tool_call(tool_call, trace_id=trace_id) # Pass trace_id
            tool_results.append({
                "tool_call": tool_call,
                "result": result
            })
        return response_text, tool_results

    def _generate_content_with_retry_and_stream(self, current_prompt_parts: List[Part]) -> Tuple[Optional[Iterable[GenerateContentResponse]], Optional[Exception]]:
        """
        Generates content from the model with retry logic for API calls and initiates the stream.
        The 'verbose' parameter is removed as logging is now handled by self.logger.

        Args:
            current_prompt_parts: The list of Parts to send to the model.

        Returns:
            A tuple containing:
                - The response stream (Iterable[GenerateContentResponse]) if successful, else None.
                - The last encountered Exception if an error occurred, else None.
        """
        response_stream: Optional[Iterable[GenerateContentResponse]] = None
        api_call_succeeded = False
        last_api_error: Optional[Exception] = None
        
        max_api_retries = self.api_retry_config.get("max_retries", 3)
        base_retry_delay = self.api_retry_config.get("base_retry_delay_seconds", 2)

        for attempt in range(max_api_retries):
            try:
                if attempt > 0: # Log only on retries
                    self.logger.info(f"Retrying API call to model (attempt {attempt + 1}/{max_api_retries})...")
                
                self.logger.debug(f"Generating content with {len(current_prompt_parts)} parts. First part type: {type(current_prompt_parts[0]) if current_prompt_parts else 'N/A'}")
                response_stream = self.model.generate_content(current_prompt_parts, stream=True)
                api_call_succeeded = True
                if attempt > 0:
                     self.logger.info("API call successful on retry.")
                break
            except google_api_exceptions.InternalServerError as e_ise:
                last_api_error = e_ise
                self.logger.warning(f"API call failed (attempt {attempt + 1}/{max_api_retries}): Internal Server Error (500). Details: {e_ise}")
                if attempt < max_api_retries - 1:
                    delay = base_retry_delay * (2**attempt)
                    self.logger.info(f"Will retry after {delay} seconds.")
                    time.sleep(delay)
                else:
                    self.logger.error("Max retries reached for API call due to Internal Server Error.")
            except google_api_exceptions.ResourceExhausted as e_re: # e.g. 429 error
                last_api_error = e_re
                self.logger.warning(f"API call failed (attempt {attempt + 1}/{max_api_retries}): Resource Exhausted ({e_re.code}). Details: {e_re}")
                if attempt < max_api_retries - 1:
                    delay = base_retry_delay * (2**attempt) # Consider checking for Retry-After header if available
                    self.logger.info(f"Will retry after {delay} seconds.")
                    time.sleep(delay)
                else:
                    self.logger.error("Max retries reached for API call due to Resource Exhausted.")
            except google_api_exceptions.GoogleAPIError as e_api:
                last_api_error = e_api
                self.logger.error(f"API call failed (attempt {attempt + 1}/{max_api_retries}): Google API Error. Code: {e_api.code if hasattr(e_api, 'code') else 'N/A'}. Details: {e_api}", exc_info=True)
                break
            except Exception as e:
                last_api_error = e
                self.logger.error(f"API call failed (attempt {attempt + 1}/{max_api_retries}) with unexpected error: {type(e).__name__} - {e}", exc_info=True)
                break
        
        if not api_call_succeeded or response_stream is None:
            self.logger.error(f"API call ultimately failed after {max_api_retries} attempts. Last error: {last_api_error}")
            return None, last_api_error
            
        self.logger.debug("API call successful, returning stream.")
        return response_stream, None

    def execute_task(self, task: str, max_iterations: int, interactive: bool) -> str:
        # Generate a unique trace ID for this task execution
        current_trace_id = uuid.uuid4().hex
        self.logger.extra['trace_id'] = current_trace_id # Set trace_id for this task
        
        self.logger.info(f"Starting task execution. Task: '{task}'. Max iterations: {max_iterations}. Interactive: {interactive}.")

        conversation_history = [Part.from_text(self.system_prompt)]
        conversation_history.append(Part.from_text(f"User: Task: {task}"))
        iteration = 0
        final_response_text = "Task execution did not produce a final agent response."

        while iteration < max_iterations:
            iteration += 1
            self.logger.info(f"Iteration {iteration} / {max_iterations}")
            
            current_prompt_parts = [p for p in conversation_history]
            # response_text = "" # Not needed here, accumulated_response_text_parts is used
            accumulated_response_text_parts = []

            response_stream, api_error = self._generate_content_with_retry_and_stream(current_prompt_parts)

            if response_stream is None:
                self.logger.error(f"Failed to generate content from model.")
                error_message = f"Error during model generation"
                if api_error:
                    error_message += f": ({type(api_error).__name__}) {api_error}"
                final_response_text = error_message
                break

            try:
                self.logger.debug("Agent (streaming): ", extra={'continued_log': True}) # Custom flag for potential special handling
                
                accumulated_response_text_parts = []

                for chunk_response in response_stream:
                    chunk_text = self._get_response_text(chunk_response)
                    if chunk_text:
                        # For verbose streaming to console, we might need a dedicated stream handler
                        # or rely on the main script's print for this specific part if self.logger.debug is too noisy.
                        # For now, let's assume self.logger.debug is fine, or a higher level like INFO if it's always desired.
                        # If we want to replicate the exact print(..., end="") behavior, that's harder with standard logging.
                        # A simple approach is to accumulate and log once, or log each chunk.
                        sys.stdout.write(chunk_text) # Replicating print(chunk_text, end="", flush=True)
                        sys.stdout.flush()
                        accumulated_response_text_parts.append(chunk_text)
                
                sys.stdout.write("\n") # Newline after streaming
                sys.stdout.flush()
                
                response_text = "".join(accumulated_response_text_parts)
                self.logger.debug(f"Full agent response (length {len(response_text)}): {response_text[:500]}{'...' if len(response_text) > 500 else ''}")
                final_response_text = response_text

            except google_api_exceptions.InternalServerError as e_stream_ise:
                self.logger.error(f"Error during model response stream: Internal Server Error (500). Details: {e_stream_ise}", exc_info=True)
                final_response_text = f"Stream error during model generation (500 Internal Server Error): {e_stream_ise}"
                break
            except google_api_exceptions.GoogleAPIError as e_stream_api:
                code = e_stream_api.code if hasattr(e_stream_api, 'code') else 'N/A'
                self.logger.error(f"Error during model response stream: Google API Error. Code: {code}. Details: {e_stream_api}", exc_info=True)
                final_response_text = f"Stream error during model generation (API Error {code}): {e_stream_api}"
                break
            except Exception as e_stream_other:
                self.logger.error(f"Error during model response stream: {type(e_stream_other).__name__} - {e_stream_other}", exc_info=True)
                final_response_text = f"Unexpected stream error during model generation: {e_stream_other}"
                break

            if not response_text and not accumulated_response_text_parts:
                self.logger.info("Model returned an empty response stream.")

            processed_response_text, tool_results = self._process_response(response_text, trace_id=current_trace_id)
            conversation_history.append(Part.from_text(f"Agent: {response_text}"))

            if not tool_results:
                self.logger.info("No tool calls detected. Task may be complete or agent needs more info.")
                break

            self.logger.debug("--- Tool Calls and Results ---")
            for tool_data in tool_results:
                tool_call_details = tool_data["tool_call"]
                tool_execution_result = tool_data["result"]
                tool_name = tool_call_details.get("tool", "Unknown tool")
                tool_params = tool_call_details.get("parameters", {})

                self.logger.debug(f"Tool Call: {tool_name}")
                self.logger.debug(f"Parameters: {json.dumps(tool_params, indent=2)}")
                self.logger.debug(f"Result: {json.dumps(tool_execution_result, indent=2)}")
                
                function_response_part = Part.from_function_response(
                    name=tool_name,
                    response={"content": tool_execution_result}
                )
                conversation_history.append(function_response_part)
            self.logger.debug("--- End Tool Calls and Results ---")
        
        if iteration >= max_iterations and not (final_response_text.startswith("Error") or final_response_text.startswith("Stream error")):
            self.logger.warning(f"Reached maximum iterations ({max_iterations}).")
            if interactive:
                while True:
                    final_response_text = self._handle_interactive_prompt(
                        conversation_history,
                        iteration,
                        current_trace_id,
                        final_response_text,
                        self.safe_mode # Pass agent_safe_mode
                    )
        self.logger.info(f"Task execution finished. Final response preview: {final_response_text[:100]}{'...' if len(final_response_text) > 100 else ''}")
        self.logger.extra['trace_id'] = None # Clear trace_id after task completion
        return final_response_text

    def execute_task_continuation(self, conversation_history: List[Part], additional_iterations: int, current_iteration_count: int, interactive: bool, trace_id: Optional[str]) -> str:
        # Set the trace_id for this continuation
        original_trace_id = self.logger.extra.get('trace_id')
        self.logger.extra['trace_id'] = trace_id
        
        self.logger.info(f"Continuing task. Additional iterations: {additional_iterations}. Current total iterations: {current_iteration_count}.")
        iteration = 0
        max_iterations_for_continuation = additional_iterations
        final_response_text = "Continuation did not produce a new agent response."
        
        while iteration < max_iterations_for_continuation:
            iteration += 1
            global_iteration = current_iteration_count + iteration
            self.logger.info(f"Continuation Iteration {global_iteration} (Local: {iteration}/{max_iterations_for_continuation})")
            
            current_prompt_parts = [p for p in conversation_history]
            accumulated_response_text_parts = []

            response_stream, api_error = self._generate_content_with_retry_and_stream(current_prompt_parts)

            if response_stream is None:
                self.logger.error(f"Failed to generate content from model during continuation.")
                error_message = f"Error during model generation in continuation"
                if api_error:
                    error_message += f": ({type(api_error).__name__}) {api_error}"
                final_response_text = error_message
                break

            try:
                self.logger.debug("Agent (streaming continuation): ", extra={'continued_log': True})
                accumulated_response_text_parts = []

                for chunk_response in response_stream:
                    chunk_text = self._get_response_text(chunk_response)
                    if chunk_text:
                        sys.stdout.write(chunk_text) # Replicating print behavior
                        sys.stdout.flush()
                        accumulated_response_text_parts.append(chunk_text)
                
                sys.stdout.write("\n") # Newline after streaming
                sys.stdout.flush()
                
                response_text = "".join(accumulated_response_text_parts)
                self.logger.debug(f"Full agent response (continuation, length {len(response_text)}): {response_text[:500]}{'...' if len(response_text) > 500 else ''}")
                final_response_text = response_text

            except google_api_exceptions.InternalServerError as e_stream_ise:
                self.logger.error(f"Error during model response stream (continuation): Internal Server Error (500). Details: {e_stream_ise}", exc_info=True)
                final_response_text = f"Stream error during model generation in continuation (500 Internal Server Error): {e_stream_ise}"
                break
            except google_api_exceptions.GoogleAPIError as e_stream_api:
                code = e_stream_api.code if hasattr(e_stream_api, 'code') else 'N/A'
                self.logger.error(f"Error during model response stream (continuation): Google API Error. Code: {code}. Details: {e_stream_api}", exc_info=True)
                final_response_text = f"Stream error during model generation in continuation (API Error {code}): {e_stream_api}"
                break
            except Exception as e_stream_other:
                self.logger.error(f"Error during model response stream (continuation): {type(e_stream_other).__name__} - {e_stream_other}", exc_info=True)
                final_response_text = f"Unexpected stream error during model generation in continuation: {e_stream_other}"
                break
            
            if not response_text and not accumulated_response_text_parts:
                 self.logger.info("Model returned an empty response stream during continuation.")

            processed_response_text, tool_results = self._process_response(response_text, trace_id=trace_id) # Pass trace_id
            conversation_history.append(Part.from_text(f"Agent: {response_text}"))

            if not tool_results:
                self.logger.info("No tool calls detected in continuation. Task may be complete.")
                break

            self.logger.debug("--- Tool Calls and Results (Continuation) ---")
            for tool_data in tool_results:
                tool_call_details = tool_data["tool_call"]
                tool_execution_result = tool_data["result"]
                tool_name = tool_call_details.get("tool", "Unknown tool")
                
                self.logger.debug(f"Tool Call: {tool_name}")
                self.logger.debug(f"Parameters: {json.dumps(tool_call_details.get('parameters', {}), indent=2)}")
                self.logger.debug(f"Result: {json.dumps(tool_execution_result, indent=2)}")

                function_response_part = Part.from_function_response(
                    name=tool_name,
                    response={"content": tool_execution_result}
                )
                conversation_history.append(function_response_part)
            self.logger.debug("--- End Tool Calls and Results (Continuation) ---")
        
        if iteration >= max_iterations_for_continuation and not (final_response_text.startswith("Error") or final_response_text.startswith("Stream error")):
            self.logger.info(f"Continuation finished its {max_iterations_for_continuation} iterations.")

        self.logger.extra['trace_id'] = original_trace_id # Restore original trace_id or None
        return final_response_text
    def _handle_interactive_prompt(self, conversation_history: List[Part], current_iteration_count: int, current_trace_id: Optional[str], initial_final_response_text: str, agent_safe_mode: bool) -> str:
        """
        Handles the interactive prompt loop for the agent, allowing the user to
        continue, provide feedback, review history, stop the task, or toggle verbose logging.

        Args:
            conversation_history: The current list of conversation parts (mutable).
            current_iteration_count: The number of iterations completed before entering the prompt.
            current_trace_id: The unique trace ID for the current task execution.
            initial_final_response_text: The agent's last response text before entering the prompt.
            agent_safe_mode: A boolean indicating if safe mode is enabled for the agent.

        Returns:
            The final response text after the interactive session concludes,
            which might be updated by subsequent agent continuations.
        """
        final_response_text = initial_final_response_text
        while True:
            # Using print here for direct user interaction, not logging.
            print("\nThe agent may need more steps or different guidance to complete the task.")
            print("\nOptions:")
            print("  [C]ontinue       - Continue for more iterations")
            print("  [F]eedback       - Provide feedback to the agent")
            print("  [R]eview History - Display conversation history")
            print("  [S]top Task      - Stop the current task")
            print("  [V]erbose Toggle - Toggle verbose logging (DEBUG/INFO)")
            try:
                choice = input("Your choice: ").strip().lower()

                if choice in ['c', 'continue']:
                    self.logger.info("User chose to [C]ontinue the task.")
                    additional_iters = self.config.get('agent_settings', {}).get('additional_iterations', 3)
                    self.logger.info(f"Continuing for {additional_iters} additional iterations.")
                    final_response_text = self.execute_task_continuation(
                        conversation_history,
                        additional_iters,
                        current_iteration_count,
                        True, # interactive is always True here
                        current_trace_id
                    )
                    break
                elif choice in ['f', 'feedback']:
                    self.logger.info("User chose to provide [F]eedback.")
                    user_feedback_text = input("Please provide your feedback or guidance for the agent: ").strip()
                    if user_feedback_text:
                        conversation_history.append(Part.from_text(f"User: {user_feedback_text}"))
                        self.logger.info(f"User feedback added to history: '{user_feedback_text[:100]}...'")
                        additional_iters = self.config.get('agent_settings', {}).get('additional_iterations', 3)
                        self.logger.info(f"Continuing with feedback for {additional_iters} additional iterations.")
                        final_response_text = self.execute_task_continuation(
                            conversation_history,
                            additional_iters,
                            current_iteration_count,
                            True, # interactive is always True here
                            current_trace_id
                        )
                        break
                    else:
                        print("No feedback provided. Please choose an option.")
                        continue
                elif choice in ['r', 'review', 'review history']:
                    self.logger.info("User chose to [R]eview History.")
                    print("\n--- Conversation History ---")
                    if not conversation_history:
                        print("History is empty.")
                    for i, part in enumerate(conversation_history):
                        print(f"[{i+1}] ", end="")
                        if part.text:
                            # Check if it's an agent or user message based on prefix
                            if part.text.startswith("Agent:"):
                                print(f"{part.text}")
                            elif part.text.startswith("User:"):
                                print(f"{part.text}")
                            else: # Default to just text if no clear prefix
                                print(f"Text: {part.text}")
                        elif part.function_call:
                            fc = part.function_call
                            print(f"Tool Call: {fc.name}, Args: {dict(fc.args)}")
                        elif part.function_response:
                            fr = part.function_response
                            # Ensure response content is extracted correctly
                            response_content = fr.response.get("content", "N/A") if isinstance(fr.response, dict) else fr.response
                            print(f"Tool Result for '{fr.name}': {response_content}")
                        else:
                            print(f"Unknown part type: {part}")
                    print("--- End of History ---\n")
                    continue # Show options again
                elif choice in ['s', 'stop', 'stop task']:
                    self.logger.info("User chose to [S]top the task.")
                    break
                elif choice in ['v', 'verbose', 'verbose toggle']:
                    current_level = self.logger.logger.getEffectiveLevel() if hasattr(self.logger, 'logger') else self.logger.getEffectiveLevel()
                    if current_level == logging.DEBUG:
                        self.logger.setLevel(logging.INFO)
                        print("Verbose logging OFF. Log level set to INFO.")
                        self.logger.info("Verbose logging OFF by user. Log level set to INFO.")
                    else:
                        self.logger.setLevel(logging.DEBUG)
                        print("Verbose logging ON. Log level set to DEBUG.")
                        self.logger.info("Verbose logging ON by user. Log level set to DEBUG.")
                    continue # Show options again
                else:
                    print(f"Invalid choice: '{choice}'. Please select from the available options.")
            except KeyboardInterrupt:
                self.logger.info("User interrupted continuation choice.")
                print("\nStopping task due to user interruption.")
                break
            except Exception as e:
                self.logger.error(f"Error in interactive loop: {e}", exc_info=True)
def main():
    """Main function to parse arguments, initialize and run the agent."""
    parser = argparse.ArgumentParser(description="Vertex AI Agent CLI")
    parser.add_argument("task", help="The task for the agent to perform.")
    parser.add_argument(
        "--max_iterations",
        type=int,
        help="Maximum number of iterations for the agent. Overrides config if set."
    )
    parser.add_argument(
        "--interactive",
        action=argparse.BooleanOptionalAction, # Use BooleanOptionalAction
        default=None, # Default to None to check if it was set
        help="Enable interactive mode. Overrides config if set. Use --interactive or --no-interactive."
    )
    parser.add_argument(
        "--config_path",
        type=str,
        default=DEFAULT_CONFIG_PATH,
        help=f"Path to the configuration file (default: {DEFAULT_CONFIG_PATH})"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging (DEBUG level) for the console. Overrides config logging.default_level for console."
    )
    parser.add_argument(
        "--safe_mode",
        action=argparse.BooleanOptionalAction,
        default=None, # Default to None to check if it was set
        help="Enable safe mode (restricts certain tool actions). Overrides config if set. Use --safe_mode or --no-safe_mode."
    )

    args = parser.parse_args()

    # Load configuration
    config = load_config(args.config_path)
    if not config:
        print(f"Error: Could not load configuration from {args.config_path}. Exiting.")
        sys.exit(1)

    # Setup logging (pass CLI verbose flag)
    setup_logging(config, verbose_cli=args.verbose)
    
    # Determine agent settings, allowing CLI overrides
    agent_settings = config.get("agent_settings", {})
    
    max_iterations_val = args.max_iterations if args.max_iterations is not None else agent_settings.get("max_iterations", 10)
    
    # Handle interactive mode: CLI > Config > Default (False)
    if args.interactive is not None:
        interactive_val = args.interactive
    else:
        interactive_val = agent_settings.get("interactive_mode", False)

    # Handle safe mode: CLI > Config > Default (True)
    if args.safe_mode is not None:
        safe_mode_val = args.safe_mode
    else:
        safe_mode_val = agent_settings.get("safe_mode", True) # Default to True if not in config

    # API Retry Configuration
    api_retry_config = config.get("api_retry_config", {"max_retries": 3, "base_retry_delay_seconds": 2})

    # Initialize agent
    try:
        agent = VertexAIAgent(
            project_id=config.get("project_id", os.environ.get("GOOGLE_CLOUD_PROJECT")),
            location=config.get("location", "us-central1"),
            model_name=config.get("model_name", "gemini-1.5-flash-001"),
            api_retry_config=api_retry_config,
            safe_mode=safe_mode_val,
            config=config # Pass the full config
        )
    except Exception as e:
        logging.error(f"Failed to initialize VertexAIAgent: {e}", exc_info=True)
        sys.exit(1)

    # Execute task
    try:
        final_response = agent.execute_task(
            task=args.task,
            max_iterations=max_iterations_val,
            interactive=interactive_val
        )
        print("\n--- Final Agent Response ---")
        print(final_response)
        print("--- End of Final Agent Response ---")
    except Exception as e:
        logging.error(f"An error occurred during task execution: {e}", exc_info=True)
        print(f"\nAn error occurred during task execution: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
