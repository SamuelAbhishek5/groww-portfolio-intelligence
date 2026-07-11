import logging
from dotenv import load_dotenv
import os
import time
from abc import ABC, abstractmethod
from typing import Optional

logger = logging.getLogger(__name__)


class BaseLLMClient(ABC):
    """Abstract interface for LLM backends used by the insight engine."""

    @abstractmethod
    def generate(self, prompt: str, system_prompt: Optional[str] = None, timeout: Optional[int] = None) -> str:
        """Generate a text response for the supplied prompt."""


class GeminiLLMClient(BaseLLMClient):
    """Lightweight Gemini client with timeout handling and retry support."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None) -> None:
        load_dotenv()  # Load environment variables from .env file
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        self.max_retries = int(os.getenv("AI_LLM_MAX_RETRIES", "3"))
        self.backoff_seconds = float(os.getenv("AI_LLM_BACKOFF_SECONDS", "0.5"))
        self.timeout = int(os.getenv("AI_LLM_TIMEOUT", "30"))
        self._client = None

    def generate(self, prompt: str, system_prompt: Optional[str] = None, timeout: Optional[int] = None) -> str:
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY is not configured.")

        try:
            from google import genai
        except ImportError as exc:  # pragma: no cover - runtime dependency guard
            raise RuntimeError("google-generativeai is not installed.") from exc

        if self._client is None:
            try:
                self._client = genai.Client(api_key=self.api_key)
                response = self._client.models.generate_content(model=self.model,contents=[system_prompt or "", prompt])
                #return response.text
            except Exception as exc:  # pragma: no cover - SDK init errors
                print(type(exc))
                print(exc)
                raise RuntimeError("Unable to initialize Gemini client.") from exc

        request_timeout = timeout or self.timeout
        last_error: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            try:
                response = self._client.models.generate_content(model=self.model, contents=[system_prompt or "", prompt])
                text = getattr(response, "text", "") or ""
                if text:
                    return text
                raise RuntimeError("Gemini returned an empty response.")
            except Exception as exc:  # pragma: no cover - network and SDK errors
                last_error = exc
                if attempt >= self.max_retries:
                    logger.warning("Gemini request failed after %s attempts: %s", attempt + 1, exc)
                    raise RuntimeError("Gemini request failed.") from exc
                logger.warning("Gemini request attempt %s failed: %s", attempt + 1, exc)
                time.sleep(self.backoff_seconds * (attempt + 1))
        if last_error is not None:
            raise RuntimeError("Gemini request failed.") from last_error
        raise RuntimeError("Gemini request failed.")
