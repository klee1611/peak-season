"""Photo classification and text extraction with strict, validated JSON output.

Invalid output gets one retry; a second failure marks the item `unclassified` (cached, so it
is not retried every run). Every result is cached by content hash.
"""

import hashlib
import json
import logging
import re
import time
from dataclasses import dataclass
from pathlib import Path
from string import Template

import httpx
from pydantic import BaseModel, Field, ValidationError

from peakseason.model.client import ChatModel
from peakseason.store import Classification, Store
from peakseason.targets import Target

log = logging.getLogger("peakseason.classify")

# iNaturalist "medium" photos are well under 1 MB.
MAX_IMAGE_BYTES = 10_000_000

RETRY_NOTE = (
    "\n\nYour previous reply was not valid. Reply with only the JSON object, "
    "using one of the listed stage ids."
)


@dataclass
class Prompt:
    version: str
    template: Template

    @classmethod
    def load(cls, path: Path) -> "Prompt":
        text = path.read_text(encoding="utf-8")
        first, _, rest = text.partition("\n")
        m = re.match(r"#\s*version:\s*(\S+)", first)
        if not m:
            raise ValueError(f"{path}: first line must be '# version: N'")
        return cls(version=m.group(1), template=Template(rest.strip()))


class PhotoResult(BaseModel):
    is_target_photo: bool
    stage: str | None = None
    progress: float | None = Field(default=None, ge=0, le=1)
    # Optional so a bare {"is_target_photo": false} is a valid rejection, not a retry.
    confidence: float | None = Field(default=None, ge=0, le=1)


class TextResult(BaseModel):
    place: str | None = None
    stage: str | None = None
    confidence: float = Field(ge=0, le=1)


def extract_json(text: str) -> dict:
    """Parse a JSON object, tolerating code fences or stray text around it."""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if not m:
            raise
        return json.loads(m.group(0))


def stage_list(target: Target) -> str:
    return "\n".join(f"- {s.id}: {s.label}" for s in target.stages)


def cache_key(*parts: str) -> str:
    return hashlib.sha256("\x1f".join(parts).encode()).hexdigest()


class Classifier:
    def __init__(
        self,
        model: ChatModel,
        store: Store,
        http: httpx.AsyncClient,
        root: Path,
    ):
        self.model = model
        self.store = store
        self.http = http
        self.root = root
        self._prompts: dict[str, Prompt] = {}
        self.latencies: list[float] = []

    def prompt(self, rel: str) -> Prompt:
        if rel not in self._prompts:
            self._prompts[rel] = Prompt.load(self.root / rel)
        return self._prompts[rel]

    def photo_key(self, target: Target, url: str) -> str:
        p = self.prompt(target.photo_prompt)
        return cache_key("photo", url, target.id, p.version, self.model.name)

    def cached_photo(self, target: Target, url: str) -> Classification | None:
        return self.store.get_classification(self.photo_key(target, url))

    async def classify_photo(self, target: Target, url: str) -> Classification:
        key = self.photo_key(target, url)
        if (hit := self.store.get_classification(key)) is not None:
            return hit
        p = self.prompt(target.photo_prompt)
        text = p.template.safe_substitute(
            display_name=target.display_name, stages=stage_list(target)
        )
        # The image is held in memory only; it is never written to disk or committed.
        image = await self._download(url)

        start = time.monotonic()
        result = await self._ask(text, image, lambda d: self._valid_photo(d, target))
        took = time.monotonic() - start
        self.latencies.append(took)
        log.info("classified %s %s -> %s in %.1fs", target.id, url, result, took)
        self.store.put_classification(key, target.id, url, result, self.model.name, took)
        return result

    async def extract_text(self, target: Target, item_id: str, place: str, snippet: str):
        p = self.prompt(target.text_prompt)
        key = cache_key("text", item_id, snippet, target.id, p.version, self.model.name)
        if (hit := self.store.get_classification(key)) is not None:
            return hit
        text = p.template.safe_substitute(
            display_name=target.display_name,
            local_names=", ".join(target.local_names.values()) or target.display_name,
            stages=stage_list(target),
            place=place,
            snippet=snippet,
        )
        start = time.monotonic()
        result = await self._ask(text, None, lambda d: self._valid_text(d, target))
        took = time.monotonic() - start
        self.store.put_classification(key, target.id, item_id, result, self.model.name, took)
        return result

    async def _download(self, url: str) -> bytes:
        """Fetch a photo, refusing anything over MAX_IMAGE_BYTES so one odd URL can't exhaust
        the runner's memory."""
        async with self.http.stream("GET", url, timeout=30, follow_redirects=True) as resp:
            resp.raise_for_status()
            chunks, size = [], 0
            async for chunk in resp.aiter_bytes():
                size += len(chunk)
                if size > MAX_IMAGE_BYTES:
                    raise httpx.HTTPError(f"photo larger than {MAX_IMAGE_BYTES} bytes: {url}")
                chunks.append(chunk)
        return b"".join(chunks)

    async def _ask(self, prompt: str, image: bytes | None, validate) -> Classification:
        for attempt in range(2):
            try:
                raw = await self.model.complete(prompt + (RETRY_NOTE if attempt else ""), image)
                return validate(extract_json(raw))
            except (json.JSONDecodeError, ValidationError, ValueError) as exc:
                log.warning("invalid model output (attempt %d): %s", attempt + 1, exc)
            except httpx.HTTPError as exc:
                log.warning("model call failed (attempt %d): %s", attempt + 1, exc)
        return Classification("unclassified", None, None, None)

    @staticmethod
    def _valid_photo(data: dict, target: Target) -> Classification:
        r = PhotoResult.model_validate(data)
        if not r.is_target_photo:
            return Classification("rejected", None, None, r.confidence)
        if r.stage not in target.stage_ids:
            raise ValueError(f"unknown stage {r.stage!r}")
        if r.confidence is None:
            raise ValueError("confidence is required for a target photo")
        return Classification("ok", r.stage, r.progress, r.confidence)

    @staticmethod
    def _valid_text(data: dict, target: Target) -> Classification:
        r = TextResult.model_validate(data)
        if r.stage is None:
            return Classification("rejected", None, None, r.confidence)
        if r.stage not in target.stage_ids:
            raise ValueError(f"unknown stage {r.stage!r}")
        return Classification("ok", r.stage, None, r.confidence)
