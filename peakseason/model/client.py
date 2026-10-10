"""Model client for any OpenAI-compatible chat endpoint (Ollama by default).

Swap providers by changing MODEL_BASE_URL / MODEL_NAME; no code changes.
"""

import base64
import logging
import time
from typing import Protocol

import httpx

log = logging.getLogger("peakseason.model")


class ChatModel(Protocol):
    name: str

    async def complete(self, prompt: str, image: bytes | None = None) -> str: ...


class OpenAICompatModel:
    def __init__(self, client: httpx.AsyncClient, base_url: str, name: str, api_key: str):
        self.client = client
        self.base_url = base_url.rstrip("/")
        self.name = name
        self.api_key = api_key

    async def complete(self, prompt: str, image: bytes | None = None) -> str:
        content: list[dict] = [{"type": "text", "text": prompt}]
        if image is not None:
            b64 = base64.b64encode(image).decode()
            content.append(
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
            )
        body = {
            "model": self.name,
            "messages": [{"role": "user", "content": content}],
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }
        start = time.monotonic()
        resp = await self.client.post(
            f"{self.base_url}/chat/completions",
            json=body,
            headers={"Authorization": f"Bearer {self.api_key}"},
        )
        took = time.monotonic() - start
        log.info("model %s -> %s in %.1fs", self.name, resp.status_code, took)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"] or ""
