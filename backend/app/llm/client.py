import json
import os
from typing import Type, TypeVar, Optional, Dict, Any
from pydantic import BaseModel
import litellm

from app.core.config import settings
from app.core.logging import logger, log_action
from app.llm.base import AbstractLLMClient

T = TypeVar("T", bound=BaseModel)

# Configure LiteLLM global settings
litellm.drop_params = True


class LiteLLMClient(AbstractLLMClient):
    """
    LiteLLM Abstraction implementation supporting primary & fallback model failover,
    usage tracking, and zero direct vendor SDK imports.
    """

    def __init__(self):
        self.primary_model = settings.LLM_MODEL
        self.fallback_model = settings.LLM_FALLBACK_MODEL
        self.api_key = settings.LLM_API_KEY

    def _extract_usage(self, response: Any, model_used: str, request_type: str) -> Dict[str, Any]:
        """Extracts token usage metadata from LiteLLM response."""
        usage_meta = {
            "model": model_used,
            "request_type": request_type,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "is_estimated": True
        }

        if hasattr(response, "usage") and response.usage:
            usage_meta["prompt_tokens"] = getattr(response.usage, "prompt_tokens", 0) or 0
            usage_meta["completion_tokens"] = getattr(response.usage, "completion_tokens", 0) or 0
            usage_meta["total_tokens"] = getattr(response.usage, "total_tokens", 0) or 0
            usage_meta["is_estimated"] = False

        return usage_meta

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: int = 2000
    ) -> Dict[str, Any]:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        if settings.LLM_API_KEY:
            os.environ["GEMINI_API_KEY"] = settings.LLM_API_KEY
            os.environ["GOOGLE_API_KEY"] = settings.LLM_API_KEY

        # Try primary model first, fallback to secondary model on error
        models_to_try = [self.primary_model, self.fallback_model]
        last_error = None

        for model in models_to_try:
            try:
                response = litellm.completion(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    api_key=self.api_key if self.api_key != "mock_key_for_testing" else None
                )
                content = response.choices[0].message.content
                usage = self._extract_usage(response, model, "completion")

                return {
                    "content": content,
                    "model": model,
                    "usage": usage
                }
            except Exception as e:
                logger.warning(f"LiteLLM call to model '{model}' failed: {e}. Trying fallback if available.")
                last_error = e

        logger.error(f"All configured LLM models failed in completion. Last error: {last_error}")
        raise RuntimeError(f"LLM completion failed across all models ({models_to_try}): {last_error}")

    def generate_structured(
        self,
        prompt: str,
        response_model: Type[T],
        system_prompt: Optional[str] = None,
        temperature: float = 0.0
    ) -> Dict[str, Any]:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        instructions = f"\n\nRespond ONLY with a valid JSON object strictly matching this schema:\n{json.dumps(response_model.model_json_schema())}"
        messages.append({"role": "user", "content": prompt + instructions})

        if settings.LLM_API_KEY:
            os.environ["GEMINI_API_KEY"] = settings.LLM_API_KEY
            os.environ["GOOGLE_API_KEY"] = settings.LLM_API_KEY

        models_to_try = [self.primary_model, self.fallback_model]
        last_error = None

        for model in models_to_try:
            try:
                response = litellm.completion(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    response_format={"type": "json_object"},
                    api_key=self.api_key if self.api_key != "mock_key_for_testing" else None
                )
                raw_text = response.choices[0].message.content
                parsed_json = json.loads(raw_text)
                validated_obj = response_model.model_validate(parsed_json)
                usage = self._extract_usage(response, model, "structured_extraction")

                return {
                    "data": validated_obj,
                    "raw_json": parsed_json,
                    "model": model,
                    "usage": usage
                }
            except Exception as e:
                logger.warning(f"Structured LiteLLM call failed with model '{model}': {e}")
                last_error = e

        logger.error(f"All structured LLM attempts failed. Error: {last_error}")
        raise RuntimeError(f"Structured LLM generation failed across all models ({models_to_try}): {last_error}")


# Singleton LLM Client
llm_client = LiteLLMClient()
