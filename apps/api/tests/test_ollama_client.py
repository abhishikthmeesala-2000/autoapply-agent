from __future__ import annotations

import json

import httpx
import pytest

from app.ai.client import (
    DEFAULT_DEEPSEEK_MODEL,
    DEFAULT_EMBEDDING_MODEL,
    DEFAULT_QWEN_MODEL,
    OllamaClient,
    OllamaConfig,
    OllamaJSONError,
    OllamaTimeoutError,
    OllamaUnavailableError,
)


def _make_client(responder):
    transport = httpx.MockTransport(responder)
    http_client = httpx.Client(transport=transport, base_url="http://localhost:11434")
    return OllamaClient(
        config=OllamaConfig(
            base_url="http://localhost:11434",
            timeout_seconds=5.0,
            qwen_model=DEFAULT_QWEN_MODEL,
            deepseek_model=DEFAULT_DEEPSEEK_MODEL,
            embedding_model=DEFAULT_EMBEDDING_MODEL,
        ),
        http_client=http_client,
    )


def test_chat_json_parses_valid_response() -> None:
    def responder(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/chat"
        payload = request.read()
        body = json.loads(payload.decode("utf-8"))
        assert body["model"] == DEFAULT_QWEN_MODEL
        return httpx.Response(200, json={"message": {"content": '{"answer": "ok"}'}})

    client = _make_client(responder)

    result = client.chat_json(
        model=DEFAULT_QWEN_MODEL,
        system_prompt="Return JSON.",
        user_prompt="Say ok.",
    )

    assert result == {"answer": "ok"}


def test_chat_json_retries_once_on_invalid_json() -> None:
    calls = {"count": 0}

    def responder(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        if calls["count"] == 1:
            return httpx.Response(200, json={"message": {"content": "not json"}})
        return httpx.Response(200, json={"message": {"content": '{"fixed": true}'}})

    client = _make_client(responder)

    result = client.chat_json(
        model=DEFAULT_DEEPSEEK_MODEL,
        system_prompt="Return JSON.",
        user_prompt="Say fixed.",
    )

    assert calls["count"] == 2
    assert result == {"fixed": True}


def test_chat_json_raises_after_retry_failure() -> None:
    def responder(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"message": {"content": "still not json"}})

    client = _make_client(responder)

    with pytest.raises(OllamaJSONError):
        client.chat_json(
            model=DEFAULT_DEEPSEEK_MODEL,
            system_prompt="Return JSON.",
            user_prompt="Say fixed.",
        )


def test_embed_returns_vector() -> None:
    def responder(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/embeddings"
        return httpx.Response(200, json={"embedding": [0.1, 0.2, 0.3]})

    client = _make_client(responder)

    embedding = client.embed(text="hello world")

    assert embedding == [0.1, 0.2, 0.3]


def test_timeout_is_converted_to_domain_error() -> None:
    def responder(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    client = _make_client(responder)

    with pytest.raises(OllamaTimeoutError):
        client.chat_json(
            model=DEFAULT_QWEN_MODEL,
            system_prompt="Return JSON.",
            user_prompt="Say ok.",
        )


def test_model_unavailable_is_reported_clearly() -> None:
    def responder(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": "model not found"})

    client = _make_client(responder)

    with pytest.raises(OllamaUnavailableError) as exc_info:
        client.chat_json(
            model=DEFAULT_QWEN_MODEL,
            system_prompt="Return JSON.",
            user_prompt="Say ok.",
        )

    assert "HTTP 404" in str(exc_info.value)
