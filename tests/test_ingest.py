"""End-to-end ingest on recorded fixtures with a fake model: no network, no Ollama."""

import json
from datetime import UTC, datetime

import httpx

from peakseason.config import ROOT, Settings
from peakseason.ingest.__main__ import run
from peakseason.store import Store

NOW = datetime(2026, 10, 9, 23, 0, tzinfo=UTC)


class FakeModel:
    name = "fake"

    def __init__(self):
        self.photo_calls = 0

    async def complete(self, prompt, image=None):
        if image is not None:
            self.photo_calls += 1
            stage = "full_bloom" if "blossom" in prompt.lower() else "peak"
            return json.dumps({"is_target_photo": True, "stage": stage, "confidence": 0.9})
        return '{"place": null, "stage": null, "confidence": 0.2}'


def settings(tmp_path, **kw):
    return Settings(
        _env_file=None,
        sqlite_path=tmp_path / "db.sqlite",
        site_data_dir=tmp_path / "out",
        spots_path=ROOT / "data" / "spots.yaml",
        **kw,
    )


async def run_once(tmp_path, model, **kw):
    from .conftest import fake_inat_handler

    return await run(
        settings(tmp_path, **kw),
        now=NOW,
        model=model,
        http_transport=httpx.MockTransport(fake_inat_handler),
    )


async def test_full_run_exports_three_countries(tmp_path):
    model = FakeModel()
    assert await run_once(tmp_path, model, max_photos_per_run=200) == 0
    out = tmp_path / "out"
    index = json.loads((out / "index.json").read_text())
    shards = set(index["shards"])
    assert {"dp", "xn", "wy"} <= shards  # Toronto, Kyoto, Seoul
    assert all("maple" in index["shards"][s]["in_season"] for s in ("dp", "xn", "wy"))

    targets = json.loads((out / "targets.json").read_text())
    assert {t["id"] for t in targets["targets"]} == {"maple", "sakura"}

    stats = json.loads((out / "run_stats.json").read_text())
    assert stats["serpapi"]["skipped"] == "no key"
    assert stats["classification"]["classified_this_run"] == model.photo_calls

    for shard in shards:
        data = json.loads((out / "shards" / f"{shard}.json").read_text())
        for cells in data["targets"].values():
            for c in cells:
                assert c["stage"] in {"green", "turning", "peak", "past_peak",
                                      "buds", "first_bloom", "full_bloom", "falling_petals",
                                      "not_enough_reports"}  # fmt: skip
                for e in c["evidence"]:
                    assert e["license"] and e["attribution"] and e["link"]


async def test_second_run_uses_cache_and_changes_nothing(tmp_path):
    first = FakeModel()
    await run_once(tmp_path, first, max_photos_per_run=200)
    second = FakeModel()
    await run_once(tmp_path, second, max_photos_per_run=200)
    assert first.photo_calls > 0 and second.photo_calls == 0
    stats = json.loads((tmp_path / "out" / "run_stats.json").read_text())
    assert stats["files_changed"] == []


async def test_budget_caps_model_calls(tmp_path):
    model = FakeModel()
    await run_once(tmp_path, model, max_photos_per_run=4)
    assert model.photo_calls == 4
    cached = Store(tmp_path / "db.sqlite").db.execute("SELECT COUNT(*) FROM classifications")
    assert cached.fetchone()[0] == 4
