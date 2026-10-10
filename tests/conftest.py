from datetime import UTC, datetime, timedelta

import pytest

from peakseason import geo
from peakseason.config import ROOT
from peakseason.reports import Report
from peakseason.targets import load_targets

NOW = datetime(2026, 10, 10, 12, 0, tzinfo=UTC)


@pytest.fixture(scope="session")
def targets():
    return {t.id: t for t in load_targets(ROOT / "targets")}


@pytest.fixture
def make_report():
    counter = iter(range(1, 10_000))

    def make(target_id="maple", lat=43.6532, lng=-79.3832, age_days=1.0, stage=None, **kw):
        n = next(counter)
        defaults = dict(
            source="inaturalist",
            kind="photo",
            target_id=target_id,
            item_id=f"inat:{n}",
            lat=lat,
            lng=lng,
            cell=geo.encode(lat, lng),
            observed_at=NOW - timedelta(days=age_days),
            link=f"https://www.inaturalist.org/observations/{n}",
            photo_url=f"https://example.org/photos/{n}/medium.jpg",
            license="cc-by",
            attribution=f"(c) someone {n}, some rights reserved (CC BY)",
            stage=stage,
            confidence=0.9 if stage else None,
        )
        defaults.update(kw)
        return Report(**defaults)

    return make


FIXTURES = ROOT / "tests" / "fixtures"
INAT_AREAS = {
    "maple": ["inat_acer_toronto", "inat_acer_kyoto", "inat_acer_seoul"],
    "sakura": ["inat_sakura_sydney"],
}


def load_fixture(name: str):
    import json

    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def fake_inat_handler(request):
    """httpx MockTransport handler that serves recorded iNaturalist fixtures."""
    import httpx

    taxa = load_fixture("taxa.json")
    sakura_ids = {
        t["id"]
        for name in ("Prunus serrulata", "Prunus × yedoensis", "Prunus × subhirtella")
        for t in taxa.get(name, {}).get("results", [])
    }
    path, q = request.url.path, request.url.params
    if request.url.host == "inaturalist-open-data.s3.amazonaws.com":
        return httpx.Response(200, content=b"\xff\xd8fake-jpeg")
    if path == "/v1/controlled_terms":
        return httpx.Response(200, json=load_fixture("controlled_terms.json"))
    if path == "/v1/taxa":
        return httpx.Response(200, json=taxa.get(q["q"], {"results": []}))
    if path == "/v1/observations":
        if int(q.get("id_above", 0)) > 0:
            return httpx.Response(200, json={"results": []})
        ids = {int(x) for x in q["taxon_id"].split(",")}
        target = "sakura" if ids & sakura_ids else "maple"
        results = [o for n in INAT_AREAS[target] for o in load_fixture(f"{n}.json")["results"]]
        return httpx.Response(200, json={"results": results})
    return httpx.Response(404, json={"error": f"unexpected {request.url}"})


@pytest.fixture(autouse=True)
def no_rate_limit(monkeypatch):
    """Tests use recorded fixtures, so there is no API to be polite to."""
    from peakseason.http import RateLimiter
    from peakseason.ingest import inaturalist

    monkeypatch.setattr(inaturalist, "RateLimiter", lambda interval: RateLimiter(0))
