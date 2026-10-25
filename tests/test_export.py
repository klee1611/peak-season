import json
import re

import pytest

from peakseason import aggregate, export
from peakseason.config import ROOT

from .conftest import NOW


def cells(targets, make_report):
    reps = [
        make_report(stage="peak", place_guess="High Park, Toronto, ON, CA"),
        make_report(stage="peak", place_guess="High Park, Toronto, ON, CA"),
        make_report("sakura", -33.8688, 151.2093, stage="buds", place_guess="Sydney, NSW, AU"),
    ]
    return {tid: aggregate.aggregate(t, reps, NOW, 7, []) for tid, t in targets.items()}


def test_shards_and_index(tmp_path, targets, make_report):
    results = cells(targets, make_report)
    tl = list(targets.values())
    export.export_targets(tmp_path, tl)
    export.export_shards(tmp_path, tl, results, NOW)

    index = json.loads((tmp_path / "index.json").read_text())
    assert set(index["shards"]) == {"dp", "r3"}
    assert index["shards"]["dp"]["go_now"] == ["maple"]
    assert index["shards"]["r3"]["go_now"] == []

    shard = json.loads((tmp_path / "shards" / "dp.json").read_text())
    [cell] = shard["targets"]["maple"]
    assert cell["stage"] == "peak" and cell["name"] == "High Park"
    assert {"link", "thumb", "license", "attribution", "taken_at"} <= set(cell["evidence"][0])
    assert shard["schema_version"] == export.SCHEMA_VERSION

    syd = json.loads((tmp_path / "shards" / "r3.json").read_text())
    assert syd["targets"]["sakura"][0]["stage"] == "not_enough_reports"


def test_unchanged_content_is_not_rewritten(tmp_path, targets, make_report):
    results = cells(targets, make_report)
    tl = list(targets.values())
    export.export_shards(tmp_path, tl, results, NOW)
    later = NOW.replace(hour=23)
    changed = export.export_shards(tmp_path, tl, results, later)
    assert not any(changed.values())


def test_stale_shards_removed(tmp_path, targets, make_report):
    tl = list(targets.values())
    export.export_shards(tmp_path, tl, cells(targets, make_report), NOW)
    changed = export.export_shards(tmp_path, tl, {t: [] for t in targets}, NOW)
    assert changed["shards/dp.json"] and not (tmp_path / "shards" / "dp.json").exists()


def test_oversized_shard_fails(tmp_path, targets, make_report, monkeypatch):
    monkeypatch.setattr(export, "MAX_SHARD_BYTES", 100)
    with pytest.raises(ValueError, match="limit"):
        export.export_shards(tmp_path, list(targets.values()), cells(targets, make_report), NOW)


def test_only_web_links_are_exported(targets, make_report):
    bad = make_report(stage="peak", place_guess="High Park, Toronto, ON, CA")
    bad.link = "javascript:alert(1)"
    bad.photo_url = "data:image/png;base64,AAAA"
    good = make_report(stage="peak", place_guess="High Park, Toronto, ON, CA")
    [cell] = aggregate.aggregate(targets["maple"], [bad, good], NOW, 7, [])
    links = [e["link"] for e in export.cell_json(cell)["evidence"]]
    assert links and all(link.startswith("https://") for link in links)


def test_thumbnails_only_from_hosts_the_csp_allows():
    ok = "https://inaturalist-open-data.s3.amazonaws.com/photos/1/medium.jpg"
    assert export.thumb_url(ok) == ok
    assert export.thumb_url("https://static.inaturalist.org/photos/1/medium.jpg")
    assert export.thumb_url("https://evil.example/photo.jpg") is None
    assert export.thumb_url("http://static.inaturalist.org/photos/1/medium.jpg") is None
    assert export.thumb_url(None) is None


def test_csp_img_src_matches_thumb_hosts():
    headers = (ROOT / "site" / "_headers").read_text(encoding="utf-8")
    img_src = re.search(r"img-src ([^;]+);", headers).group(1).split()
    allowed = {u.removeprefix("https://") for u in img_src if u.startswith("https://")}
    assert allowed == set(export.THUMB_HOSTS)
