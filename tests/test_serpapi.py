from datetime import timedelta

import httpx
import pytest

from peakseason.config import Settings
from peakseason.ingest import serpapi
from peakseason.spots import Spot
from peakseason.store import Store

from .conftest import NOW, load_fixture

ARASHIYAMA = Spot(
    name="Arashiyama", local_name="嵐山", lat=35.0090, lng=135.6745, country="JP", lang="ja",
    known_for=["maple"],
)  # fmt: skip
CENTRAL_PARK = Spot(
    name="Central Park", lat=40.7828, lng=-73.9654, country="US", lang="en", known_for=["maple"]
)


def test_plan_only_in_season_and_under_reported(targets, make_report):
    t = targets["maple"]
    nearby = make_report(lat=35.02, lng=135.70)  # Kyoto, in season, unclassified
    planned = serpapi.plan_queries([t], [ARASHIYAMA, CENTRAL_PARK], [nearby], NOW, 7)
    assert [p.spot.name for p in planned] == ["Arashiyama"]
    assert planned[0].query == '"嵐山" 紅葉 見頃'


def test_plan_skips_well_reported_spot(targets, make_report):
    reps = [make_report(lat=35.0091, lng=135.6746, stage="peak") for _ in range(3)]
    assert serpapi.plan_queries([targets["maple"]], [ARASHIYAMA], reps, NOW, 7) == []


def test_plan_ignores_old_reports(targets, make_report):
    old = make_report(lat=35.02, lng=135.70, age_days=9)
    assert serpapi.plan_queries([targets["maple"]], [ARASHIYAMA], [old], NOW, 7) == []


@pytest.mark.parametrize(
    "left,reserve,per_run,expected",
    [(None, 20, 10, 0), (64, 20, 10, 10), (25, 20, 10, 5), (20, 20, 10, 0), (5, 20, 10, 0)],
)
def test_allowed_calls(left, reserve, per_run, expected):
    assert serpapi.allowed_calls(left, reserve, per_run) == expected


def make_client(handler, tmp_path, **settings):
    s = Settings(_env_file=None, sqlite_path=tmp_path / "db", **settings)
    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return serpapi.SerpApiClient(http, Store(":memory:"), s), http


def recording_handler(calls, account=200):
    def handler(request):
        calls.append(request.url.path)
        if request.url.path == "/account.json":
            if account != 200:
                return httpx.Response(account)
            return httpx.Response(200, json=load_fixture("serpapi_account.json"))
        assert request.url.params["tbs"] == "qdr:w"
        assert request.url.params["hl"] == "ja" and request.url.params["gl"] == "jp"
        return httpx.Response(200, json=load_fixture("serpapi_search_ja.json"))

    return handler


def planned(targets):
    return [serpapi.PlannedQuery(targets["maple"], ARASHIYAMA, '"嵐山" 紅葉 見頃')]


async def test_no_key_makes_no_calls(targets, tmp_path):
    calls = []
    client, http = make_client(recording_handler(calls), tmp_path)
    stats = {}
    async with http:
        assert await client.fetch(planned(targets), stats) == []
    assert calls == [] and stats["serpapi"]["skipped"] == "no key"


async def test_account_api_down_means_zero_searches(targets, tmp_path):
    calls = []
    client, http = make_client(recording_handler(calls, account=503), tmp_path, serpapi_api_key="k")
    async with http:
        assert await client.fetch(planned(targets), {}) == []
    assert "/search.json" not in calls


async def test_search_then_cache(targets, tmp_path):
    calls = []
    client, http = make_client(recording_handler(calls), tmp_path, serpapi_api_key="k")
    stats = {}
    async with http:
        first = await client.fetch(planned(targets), stats)
        second = await client.fetch(planned(targets), {})
    assert calls.count("/search.json") == 1  # second run served from the 48 h cache
    assert len(first) == 2 and len(second) == 2  # result without a link is dropped
    r = first[0]
    assert (r.kind, r.source, r.cell, r.spot_id) == (
        "text",
        "serpapi",
        ARASHIYAMA.cell,
        "arashiyama",
    )
    assert "見頃" in r.text and r.link.startswith("https://")
    assert stats["serpapi"]["calls"] == 1


async def test_per_run_cap(targets, tmp_path):
    calls = []
    client, http = make_client(
        recording_handler(calls), tmp_path, serpapi_api_key="k", serpapi_max_calls_per_run=1
    )
    many = [
        serpapi.PlannedQuery(targets["maple"], ARASHIYAMA, f'"嵐山" 紅葉 {i}') for i in range(4)
    ]
    stats = {}
    async with http:
        await client.fetch(many, stats)
    assert calls.count("/search.json") == 1
    assert stats["serpapi"]["skipped_for_budget"] == 3


def test_text_report_age_from_fetch_time(targets):
    resp = dict(load_fixture("serpapi_search_ja.json"))
    resp["peakseason_fetched_at"] = (NOW - timedelta(days=2)).isoformat()
    [r, _] = serpapi.to_reports(planned(targets)[0], resp)
    assert r.observed_at == NOW - timedelta(days=2)
