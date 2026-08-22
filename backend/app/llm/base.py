from abc import ABC, abstractmethod
from typing import Any, Optional, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class AbstractLLMClient(ABC):
    """Abstract LLM Interface enforcing vendor independence."""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 2000
    ) -> dict[str, Any]:
        """Generates standard text completion and returns response + usage metadata."""

    @abstractmethod
    def generate_structured(
        self,
        prompt: str,
        response_model: type[T],
        system_prompt: str | None = None,
        temperature: float = 0.0
    ) -> dict[str, Any]:
        """Generates Pydantic structured output and returns parsed object + usage metadata."""
