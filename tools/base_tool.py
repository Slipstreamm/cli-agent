from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class BaseTool(ABC):
    @abstractmethod
    def get_name(self) -> str:
        """Returns the callable name of the tool."""
        pass

    @abstractmethod
    def get_description(self) -> str:
        """Returns a description of the tool for the LLM."""
        pass

    @abstractmethod
    def get_parameters_schema(self) -> Dict[str, Any]:
        """Returns a dictionary representing a simplified schema of parameters."""
        pass

    @abstractmethod
    def execute(
        self, agent_safe_mode: bool = False, trace_id: Optional[str] = None, **kwargs
    ) -> Dict[str, Any]:
        """
        The method that performs the tool's action and returns a result dictionary.

        Args:
            agent_safe_mode (bool): Indicates if the agent is in safe mode.
            trace_id (Optional[str]): An optional trace ID for logging/tracking.
            **kwargs: Tool-specific parameters.

        Returns:
            Dict[str, Any]: A dictionary containing the result of the tool's execution.
        """
        pass
