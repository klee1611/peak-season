"""SerpApi fetcher: recent web results about famous spots, turned into text reports.

Optional and strictly budgeted (the free plan is ~100 searches/month):
- No SERPAPI_API_KEY -> skipped, with a log line.
- Budget source of truth is SerpApi's Account API (free, does not use a search). If it can't
  be read, this run makes zero searches. Calls stop while searches left would drop below
  SERPAPI_RESERVE, and never exceed SERPAPI_MAX_CALLS_PER_RUN.
- Only famous spots where the target is in season nearby (recent iNaturalist reports) but the
  spot itself has fewer than MIN_SPOT_REPORTS stage reports.
- Each (target, spot, query) response is cached for SERPAPI_CACHE_HOURS; no re-query before.

Docs: https://serpapi.com/account-api, https://serpapi.com/search-api
"""

import hashlib
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import httpx

from peakseason import geo
from peakseason.config import Settings
from peakseason.http import get_json
from peakseason.reports import Report
from peakseason.spots import Spot
from peakseason.store import Store
from peakseason.targets import Target

log = logging.getLogger("peakseason.serpapi")

ACCOUNT_URL = "https://serpapi.com/account.json"
SEARCH_URL = "https://serpapi.com/search.json"
MIN_SPOT_REPORTS = 3
IN_SEASON_RADIUS_KM = 50.0
RESULTS_PER_QUERY = 5


@dataclass
class PlannedQuery:
    target: Target
    spot: Spot
    query: str


def plan_queries(
    targets: list[Target], spots: list[Spot], reports: list[Report], now: datetime, window_days: int
) -> list[PlannedQuery]:
    """Famous spots where the target is in season nearby but under-reported at the spot."""
    since = now - timedelta(days=window_days)
    recent = [r for r in reports if r.source == "inaturalist" and r.observed_at >= since]
    planned = []
    for t in targets:
        mine = [r for r in recent if r.target_id == t.id]
        for s in spots:
            if t.id not in s.known_for:
                continue
            template = t.search_queries.get(s.lang) or t.search_queries.get("en")
            if not template:
                continue
            nearby = any(
                geo.haversine_km(s.lat, s.lng, r.lat, r.lng) <= IN_SEASON_RADIUS_KM for r in mine
            )
            at_spot = sum(1 for r in mine if r.cell == s.cell and r.stage is not None)
            if nearby and at_spot < MIN_SPOT_REPORTS:
                planned.append(PlannedQuery(t, s, template.replace("{place}", s.query_name())))
    return planned


def allowed_calls(searches_left: int | None, reserve: int, per_run: int) -> int:
    if searches_left is None:
        return 0  # Account API unreachable: spend nothing this run.
    return max(0, min(per_run, searches_left - reserve))


def to_reports(pq: PlannedQuery, response: dict) -> list[Report]:
    """Organic results -> text reports for the spot's cell (link to the source, no images)."""
    fetched = response.get("peakseason_fetched_at")
    observed_at = datetime.fromisoformat(fetched) if fetched else datetime.now(UTC)
    out = []
    for res in (response.get("organic_results") or [])[:RESULTS_PER_QUERY]:
        link, snippet = res.get("link"), res.get("snippet") or ""
        if not link:
            continue
        title = res.get("title") or ""
        out.append(
            Report(
                source="serpapi",
                kind="text",
                target_id=pq.target.id,
                item_id="serp:" + hashlib.sha256(link.encode()).hexdigest()[:16],
                lat=pq.spot.lat,
                lng=pq.spot.lng,
                cell=pq.spot.cell,
                observed_at=observed_at,
                link=link,
                place_guess=pq.spot.name,
                text=f"{title}\n{snippet}".strip(),
                title=title or None,
                spot_id=pq.spot.id,
            )
        )
    return out


class SerpApiClient:
    def __init__(self, client: httpx.AsyncClient, store: Store, settings: Settings):
        self.client = client
        self.store = store
        self.settings = settings
        self.key = settings.serpapi_api_key

    async def searches_left(self) -> int | None:
        try:
            data = await get_json(
                self.client, ACCOUNT_URL, params={"api_key": self.key}, label="serpapi", retries=1
            )
            return int(data["total_searches_left"])
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
            log.warning("serpapi: Account API unavailable (%s); making no searches this run", exc)
            return None

    async def search(self, pq: PlannedQuery) -> dict:
        params = {
            "engine": "google",
            "q": pq.query,
            "hl": pq.spot.lang,
            "gl": pq.spot.country.lower(),
            "tbs": "qdr:w",  # past week
            "api_key": self.key,
        }
        data = await get_json(self.client, SEARCH_URL, params=params, label="serpapi", retries=1)
        keep = [
            {k: r.get(k) for k in ("title", "link", "snippet", "date")}
            for r in (data.get("organic_results") or [])[:RESULTS_PER_QUERY]
        ]
        return {
            "organic_results": keep,
            "peakseason_fetched_at": datetime.now(UTC).isoformat(),
        }

    async def fetch(self, planned: list[PlannedQuery], stats: dict) -> list[Report]:
        s = self.settings
        stats["serpapi"] = info = {"planned": len(planned), "cached": 0, "calls": 0}
        if not self.key:
            log.info("serpapi: SERPAPI_API_KEY not set; running on iNaturalist alone")
            info["skipped"] = "no key"
            return []
        max_age = s.serpapi_cache_hours * 3600
        reports: list[Report] = []
        todo = []
        for pq in planned:
            cached = self.store.get_serpapi(pq.target.id, pq.spot.id, pq.query, max_age)
            if cached is not None:
                info["cached"] += 1
                reports += to_reports(pq, cached)
            else:
                todo.append(pq)
        if not todo:
            return reports

        left = await self.searches_left()
        budget = allowed_calls(left, s.serpapi_reserve, s.serpapi_max_calls_per_run)
        info.update(searches_left_at_start=left, allowed=budget)
        log.info("serpapi: %d to query, %s searches left, %d allowed", len(todo), left, budget)
        for pq in todo[:budget]:
            try:
                resp = await self.search(pq)
            except httpx.HTTPError as exc:
                log.warning("serpapi: search failed for %s (%s)", pq.spot.name, exc)
                self.store.log_serpapi(pq.target.id, pq.spot.id, pq.query, "error")
                info["calls"] += 1
                continue
            info["calls"] += 1
            self.store.put_serpapi(pq.target.id, pq.spot.id, pq.query, resp)
            self.store.log_serpapi(pq.target.id, pq.spot.id, pq.query, "ok")
            reports += to_reports(pq, resp)
        info["skipped_for_budget"] = max(0, len(todo) - budget)
        return reports
