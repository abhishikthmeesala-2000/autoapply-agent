from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

import httpx
from pydantic import BaseModel, Field

DEFAULT_QWEN_MODEL = "qwen3"
DEFAULT_DEEPSEEK_MODEL = "deepseek-r1"
DEFAULT_EMBEDDING_MODEL = "bge-m3"


class OllamaError(RuntimeError):
    pass


class OllamaTimeoutError(OllamaError):
    pass


class OllamaUnavailableError(OllamaError):
    pass


class OllamaJSONError(OllamaError):
    pass


class OllamaConfig(BaseModel):
    base_url: str = Field(default="http://localhost:11434")
    timeout_seconds: float = Field(default=60.0, gt=0)
    qwen_model: str = Field(default=DEFAULT_QWEN_MODEL)
    deepseek_model: str = Field(default=DEFAULT_DEEPSEEK_MODEL)
    embedding_model: str = Field(default=DEFAULT_EMBEDDING_MODEL)

    @classmethod
    def from_env(cls) -> "OllamaConfig":
        return cls(
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            timeout_seconds=float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "60")),
            qwen_model=os.getenv("OLLAMA_QWEN_MODEL", DEFAULT_QWEN_MODEL),
            deepseek_model=os.getenv("OLLAMA_DEEPSEEK_MODEL", DEFAULT_DEEPSEEK_MODEL),
            embedding_model=os.getenv("OLLAMA_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL),
        )


@dataclass(frozen=True)
class OllamaResponse:
    raw_text: str
    json_data: Optional[Dict[str, Any]]


class OllamaClient:
    def __init__(
        self,
        config: Optional[OllamaConfig] = None,
        http_client: Optional[httpx.Client] = None,
    ) -> None:
        self.config = config or OllamaConfig.from_env()
        self._client = http_client or httpx.Client(
            base_url=self.config.base_url, timeout=self.config.timeout_seconds
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "OllamaClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def chat_json(
        self,
        *,
        model: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
        max_retries: int = 1,
    ) -> Dict[str, Any]:
        last_error: Optional[Exception] = None
        prompt = user_prompt

        for attempt in range(max_retries + 1):
            response_text = self._chat(
                model=model,
                system_prompt=system_prompt,
                user_prompt=prompt,
                temperature=temperature,
            )
            try:
                return json.loads(response_text)
            except json.JSONDecodeError as exc:
                last_error = exc
                if attempt >= max_retries:
                    break
                prompt = (
                    f"{user_prompt}\n\n"
                    "Your previous response was invalid JSON. "
                    "Return only strict JSON and no markdown, explanation, or code fences."
                )

        raise OllamaJSONError(
            f"Model {model} returned invalid JSON after {max_retries + 1} attempt(s)."
        ) from last_error

    def embed(self, *, text: str, model: Optional[str] = None) -> list[float]:
        payload = {
            "model": model or self.config.embedding_model,
            "prompt": text,
        }

        data = self._post("/api/embeddings", payload)
        embedding = data.get("embedding")
        if not isinstance(embedding, list) or not all(
            isinstance(value, (int, float)) for value in embedding
        ):
            raise OllamaError(
                "Ollama embeddings response did not contain a valid embedding vector."
            )

        return [float(value) for value in embedding]

    def _chat(
        self,
        *,
        model: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
    ) -> str:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "options": {"temperature": temperature},
            "format": "json",
        }

        data = self._post("/api/chat", payload)
        message = data.get("message")
        if not isinstance(message, dict):
            raise OllamaError("Ollama chat response is missing a message payload.")

        content = message.get("content")
        if not isinstance(content, str):
            raise OllamaError("Ollama chat response did not include message content.")

        return content

    def _post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            response = self._client.post(path, json=payload)
        except httpx.TimeoutException as exc:
            raise OllamaTimeoutError(
                f"Timed out while calling Ollama at {self.config.base_url}."
            ) from exc
        except httpx.RequestError as exc:
            raise OllamaUnavailableError(
                f"Unable to reach Ollama at {self.config.base_url}: {exc}"
            ) from exc

        if response.status_code in (404, 502, 503, 504):
            raise OllamaUnavailableError(
                f"Ollama model endpoint returned HTTP {response.status_code} at {path}."
            )

        if response.is_error:
            raise OllamaError(
                f"Ollama request to {path} failed with HTTP {response.status_code}: {response.text}"
            )

        try:
            return response.json()
        except ValueError as exc:
            raise OllamaError("Ollama returned a non-JSON response body.") from exc
