"""Requests-based DeepSeek client for networks where httpx POST is unstable."""

from __future__ import annotations

import json
import time
from collections.abc import Iterator
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app.core.errors import AppError


class DeepSeekChatClient:
    def __init__(self, api_key: str, base_url: str, model: str, timeout: int) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.session = requests.Session()
        retry = Retry(
            total=3,
            connect=3,
            read=0,
            status=3,
            backoff_factor=0.5,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset({"POST"}),
        )
        self.session.mount("https://", HTTPAdapter(max_retries=retry))
        self.session.mount("http://", HTTPAdapter(max_retries=retry))

    def complete(
        self,
        messages: list[dict[str, str]],
        temperature: float,
        json_mode: bool = False,
    ) -> tuple[str, dict[str, int] | None]:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        response = self._post(payload, stream=False)
        data = response.json()
        content = str(data["choices"][0]["message"]["content"])
        usage = data.get("usage") or {}
        return content, {
            "input_tokens": int(usage.get("prompt_tokens") or 0),
            "output_tokens": int(usage.get("completion_tokens") or 0),
        }

    def stream(self, messages: list[dict[str, str]], temperature: float) -> Iterator[tuple[str, dict[str, int] | None]]:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
        }
        response = self._post(payload, stream=True)
        usage: dict[str, int] | None = None
        try:
            for raw_line in response.iter_lines(decode_unicode=True):
                if not raw_line:
                    continue
                line = raw_line.strip()
                if not line.startswith("data:"):
                    continue
                data_text = line[5:].strip()
                if data_text == "[DONE]":
                    break
                data = json.loads(data_text)
                choices = data.get("choices") or []
                if choices:
                    content = choices[0].get("delta", {}).get("content")
                    if content:
                        yield str(content), None
                raw_usage = data.get("usage")
                if raw_usage:
                    usage = {
                        "input_tokens": int(raw_usage.get("prompt_tokens") or 0),
                        "output_tokens": int(raw_usage.get("completion_tokens") or 0),
                    }
            yield "", usage or {"input_tokens": 0, "output_tokens": 0}
        except requests.RequestException as exc:
            raise AppError("MODEL_TIMEOUT", "DeepSeek streaming response timed out.", 504) from exc

    def _post(self, payload: dict[str, Any], stream: bool) -> requests.Response:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                response = self.session.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=(10, self.timeout),
                    stream=stream,
                )
                if response.status_code == 401:
                    raise AppError("MODEL_UNAUTHORIZED", "DeepSeek API Key is invalid.", 502)
                if response.status_code == 429:
                    raise AppError("RATE_LIMITED", "DeepSeek rate limit reached.", 429)
                response.raise_for_status()
                return response
            except AppError:
                raise
            except requests.Timeout as exc:
                last_error = exc
            except requests.ConnectionError as exc:
                last_error = exc
            except requests.HTTPError as exc:
                raise AppError(
                    "MODEL_UNAVAILABLE",
                    f"DeepSeek request failed with HTTP {response.status_code}.",
                    503,
                ) from exc
            if attempt < 2:
                time.sleep(0.5 * (attempt + 1))
        raise AppError("MODEL_TIMEOUT", "Unable to connect to DeepSeek.", 504) from last_error
