from datetime import date

import httpx
import pytest

from peakseason.ingest.inaturalist import INatClient, normalize
from peakseason.store import Store

from .conftest import fake_inat_handler, load_fixture


@pytest.fixture
async def inat():
    transport = httpx.MockTransport(fake_inat_handler)
    async with httpx.AsyncClient(transport=transport) as client:
        yield INatClient(client, Store(":memory:"))


async def test_resolve_taxa(inat, targets):
    assert len(await inat.resolve_taxa(targets["maple"])) == 1
    sakura = await inat.resolve_taxa(targets["sakura"])
    assert len(sakura) >= 2  # names missing from the fixture are skipped, not guessed


async def test_controlled_terms(inat):
    terms = await inat.controlled_terms()
    labels = {label for label, _ in terms.values()}
    assert {"Leaves", "Flowers and Fruits"} <= labels


async def test_paging_with_id_above():
    seen = []

    def handler(request):
        id_above = int(request.url.params["id_above"])
        seen.append(id_above)
        if id_above == 0:
            return httpx.Response(200, json={"results": [{"id": i} for i in range(1, 201)]})
        return httpx.Response(200, json={"results": [{"id": 201}]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        inat = INatClient(client, Store(":memory:"))
        got = [o["id"] async for o in inat.observations([1], date(2026, 10, 1))]
    assert seen == [0, 200]
    assert got[-1] == 201 and len(got) == 201


@pytest.mark.parametrize(
    "fixture,target", [
        ("inat_acer_toronto.json", "maple"),
        ("inat_acer_kyoto.json", "maple"),
        ("inat_acer_seoul.json", "maple"),
        ("inat_sakura_sydney.json", "sakura"),
    ],
)  # fmt: skip
async def test_normalize_real_fixtures(inat, targets, fixture, target):
    terms = await inat.controlled_terms()
    reports = [normalize(o, targets[target], terms) for o in load_fixture(fixture)["results"]]
    usable = [r for r in reports if r]
    assert usable
    for r in usable:
        assert r.cell and len(r.cell) == 5
        assert r.link.startswith("https://www.inaturalist.org/observations/")
        if r.photo_url:
            assert r.license and r.license.startswith("cc")
            assert "/medium." in r.photo_url


def _obs(**over):
    base = load_fixture("inat_acer_toronto.json")["results"][0]
    return {**base, **over}


@pytest.mark.parametrize(
    "over",
    [
        {"obscured": True},
        {"geoprivacy": "obscured"},
        {"taxon_geoprivacy": "private"},
        {"location": None},
        {"positional_accuracy": 25_000},
        {"time_observed_at": None, "observed_on": None},
    ],
)
def test_unusable_observations_skipped(targets, over):
    assert normalize(_obs(**over), targets["maple"], {}) is None


def test_unlicensed_photo_never_used(targets):
    obs = _obs(photos=[{"id": 1, "url": "https://x/square.jpg", "license_code": None}])
    r = normalize(obs, targets["maple"], {})
    assert r is not None and r.photo_url is None and r.license is None


async def test_annotation_becomes_signal(inat, targets):
    terms = await inat.controlled_terms()
    leaves = next(tid for tid, (label, _) in terms.items() if label == "Leaves")
    colored = next(v for v, lbl in terms[leaves][1].items() if lbl == "Colored Leaves")
    ann = {"controlled_attribute_id": leaves, "controlled_value_id": colored, "vote_score": 1}
    r = normalize(_obs(annotations=[ann]), targets["maple"], terms)
    assert r.in_season_signal and r.stage is None
    ann["vote_score"] = -1
    assert not normalize(_obs(annotations=[ann]), targets["maple"], terms).in_season_signal
