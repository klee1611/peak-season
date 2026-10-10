"""iNaturalist fetcher: recent observations of a target's taxa, worldwide, with photos.

API docs: https://api.inaturalist.org/v1/docs/  (no key; stay at <= 1 request/second)
"""

import logging
from collections.abc import AsyncIterator
from datetime import UTC, date, datetime

import httpx

from peakseason import geo
from peakseason.http import RateLimiter, get_json
from peakseason.reports import Report
from peakseason.store import Store
from peakseason.targets import Target

log = logging.getLogger("peakseason.inaturalist")

API = "https://api.inaturalist.org/v1"
PER_PAGE = 200
# Licenses that allow us to show the photo (with attribution). Anything else, including
# "all rights reserved" (license_code null), is never shown and never sent to the model.
DISPLAYABLE_LICENSES = {
    "cc0",
    "cc-by",
    "cc-by-nc",
    "cc-by-sa",
    "cc-by-nd",
    "cc-by-nc-sa",
    "cc-by-nc-nd",
}
# Observations with worse location accuracy than this are too vague to send people to.
MAX_POSITIONAL_ACCURACY_M = 5000
TAXA_CACHE_S = 30 * 86400


class INatClient:
    def __init__(self, client: httpx.AsyncClient, store: Store):
        self.client = client
        self.store = store
        self.limiter = RateLimiter(1.0)

    async def _get(self, path: str, params: dict | None = None) -> dict:
        return await get_json(
            self.client, f"{API}{path}", params=params, label="inat", limiter=self.limiter
        )

    async def resolve_taxa(self, target: Target) -> list[int]:
        """Resolve taxon names to IDs (cached). Names that don't resolve are logged and skipped."""
        ids: list[int] = []
        for taxon in target.inat_taxa:
            key = f"taxon:{taxon.rank}:{taxon.name}"
            cached = self.store.get_json(key, TAXA_CACHE_S)
            if cached is None:
                data = await self._get("/taxa", {"q": taxon.name, "rank": taxon.rank})
                match = next((t for t in data.get("results", []) if t["name"] == taxon.name), None)
                cached = match["id"] if match else 0
                self.store.put_json(key, cached)
            if cached:
                ids.append(cached)
            else:
                log.warning("%s: taxon %r (%s) did not resolve", target.id, taxon.name, taxon.rank)
        return ids

    async def controlled_terms(self) -> dict[int, tuple[str, dict[int, str]]]:
        """term_id -> (term label, {value_id: value label}), from /v1/controlled_terms (cached)."""
        cached = self.store.get_json("controlled_terms", TAXA_CACHE_S)
        if cached is None:
            data = await self._get("/controlled_terms")
            cached = {
                str(t["id"]): [t["label"], {str(v["id"]): v["label"] for v in t["values"]}]
                for t in data["results"]
            }
            self.store.put_json("controlled_terms", cached)
        return {int(k): (v[0], {int(i): lbl for i, lbl in v[1].items()}) for k, v in cached.items()}

    async def observations(
        self,
        taxon_ids: list[int],
        since: date,
        bbox: tuple[float, float, float, float] | None = None,
        max_pages: int = 200,
    ) -> AsyncIterator[dict]:
        """All matching observations, oldest id first, paged with id_above.

        Deep `page=` numbers are capped by the API, so we page by id instead.
        """
        params: dict = {
            "taxon_id": ",".join(map(str, taxon_ids)),
            "d1": since.isoformat(),
            "photos": "true",
            "per_page": PER_PAGE,
            "order_by": "id",
            "order": "asc",
        }
        if bbox:
            params.update(swlng=bbox[0], swlat=bbox[1], nelng=bbox[2], nelat=bbox[3])
        id_above = 0
        for _ in range(max_pages):
            data = await self._get("/observations", {**params, "id_above": id_above})
            results = data.get("results", [])
            for obs in results:
                yield obs
            if len(results) < PER_PAGE:
                return
            id_above = results[-1]["id"]
        log.warning("inat: stopped after %d pages", max_pages)


def _observed_at(obs: dict) -> datetime | None:
    if obs.get("time_observed_at"):
        return datetime.fromisoformat(obs["time_observed_at"]).astimezone(UTC)
    if obs.get("observed_on"):
        # Date only: use local noon-ish as a neutral time.
        d = date.fromisoformat(obs["observed_on"])
        return datetime(d.year, d.month, d.day, 12, tzinfo=UTC)
    return None


def annotation_labels(obs: dict, terms: dict[int, tuple[str, dict[int, str]]]) -> list[str]:
    """Labels of annotation values on this observation that the community hasn't voted down."""
    labels = []
    for ann in obs.get("annotations") or []:
        if ann.get("vote_score", 0) < 0:
            continue
        term = terms.get(ann.get("controlled_attribute_id"))
        if term and (value := term[1].get(ann.get("controlled_value_id"))):
            labels.append(f"{term[0]}={value}")
    return labels


def normalize(
    obs: dict, target: Target, terms: dict[int, tuple[str, dict[int, str]]]
) -> Report | None:
    """Turn one raw observation into a Report, or None if it can't be used."""
    if obs.get("obscured") or obs.get("geoprivacy") in ("obscured", "private"):
        return None
    if obs.get("taxon_geoprivacy") in ("obscured", "private"):
        return None
    if not obs.get("location"):
        return None
    if (obs.get("positional_accuracy") or 0) > MAX_POSITIONAL_ACCURACY_M:
        return None
    observed_at = _observed_at(obs)
    if observed_at is None:
        return None
    lat_s, lng_s = obs["location"].split(",")
    lat, lng = float(lat_s), float(lng_s)

    photo = next(
        (
            p
            for p in obs.get("photos") or []
            if p.get("license_code") in DISPLAYABLE_LICENSES and not p.get("hidden")
        ),
        None,
    )
    labels = annotation_labels(obs, terms)
    signal = False
    if target.inat_annotation:
        wanted = {f"{target.inat_annotation.term}={v}" for v in target.inat_annotation.in_season}
        signal = bool(wanted & set(labels))

    return Report(
        source="inaturalist",
        kind="photo",
        target_id=target.id,
        item_id=f"inat:{obs['id']}",
        lat=lat,
        lng=lng,
        cell=geo.encode(lat, lng),
        observed_at=observed_at,
        link=obs.get("uri") or f"https://www.inaturalist.org/observations/{obs['id']}",
        place_guess=obs.get("place_guess"),
        # iNaturalist serves several sizes at the same path; "medium" is ~500 px.
        photo_url=photo["url"].replace("/square.", "/medium.") if photo else None,
        license=photo["license_code"] if photo else None,
        attribution=photo.get("attribution") if photo else None,
        annotations=labels,
        in_season_signal=signal,
    )
