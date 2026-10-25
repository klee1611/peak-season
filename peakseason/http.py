"""Shared HTTP helper: timeouts, retries with backoff, rate limiting, one log line per call."""

import asyncio
import logging
import time

import httpx

log = logging.getLogger("peakseason.http")

RETRY_STATUSES = {429, 500, 502, 503, 504}


class RateLimiter:
    """At most one request per `interval` seconds (iNaturalist asks for <= 1 req/s)."""

    def __init__(self, interval: float):
        self.interval = interval
        self._last = 0.0
        self._lock = asyncio.Lock()

    async def wait(self) -> None:
        async with self._lock:
            delay = self._last + self.interval - time.monotonic()
            if delay > 0:
                await asyncio.sleep(delay)
            self._last = time.monotonic()


async def get_json(
    client: httpx.AsyncClient,
    url: str,
    *,
    params: dict | None = None,
    label: str,
    limiter: RateLimiter | None = None,
    retries: int = 3,
    redact: tuple[str, ...] = ("api_key",),
) -> dict:
    """GET a JSON document. `label` names the source in logs; `redact` params never get logged."""
    shown = {k: ("***" if k in redact else v) for k, v in (params or {}).items()}
    for attempt in range(retries + 1):
        if limiter:
            await limiter.wait()
        start = time.monotonic()
        try:
            resp = await client.get(url, params=params)
            took = time.monotonic() - start
            log.info("%s GET %s %s -> %s in %.2fs", label, url, shown, resp.status_code, took)
            if resp.status_code in RETRY_STATUSES and attempt < retries:
                await asyncio.sleep(2**attempt)
                continue
            if resp.is_error:
                # Not raise_for_status(): httpx's message carries the full URL, query string and
                # all, and callers log it, which would print the api_key.
                raise httpx.HTTPStatusError(
                    f"{label} GET {url} -> {resp.status_code}",
                    request=resp.request,
                    response=resp,
                )
            return resp.json()
        except (httpx.TransportError, httpx.TimeoutException) as exc:
            log.warning("%s GET %s failed (%s), attempt %d", label, url, exc, attempt + 1)
            if attempt >= retries:
                raise
            await asyncio.sleep(2**attempt)
    raise RuntimeError("unreachable")
