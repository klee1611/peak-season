import json
import re

import pytest

from peakseason import aggregate, export, pages
from peakseason.config import ROOT, Settings
from peakseason.spots import load_spots

from .conftest import NOW

ARASHIYAMA = (35.0090, 135.6745)
SITE_URL = "https://example.test"


@pytest.fixture
def site(tmp_path, targets, make_report):
    """A tiny exported site: Arashiyama at peak for maple, with a hostile attribution."""
    spots = load_spots(ROOT / "data" / "spots.yaml")
    reps = [
        make_report(
            stage="peak",
            lat=ARASHIYAMA[0],
            lng=ARASHIYAMA[1],
            attribution='(c) <script>alert(1)</script> "x"',
        ),
        make_report(stage="peak", lat=ARASHIYAMA[0], lng=ARASHIYAMA[1]),
    ]
    data_dir = tmp_path / "data"
    tl = list(targets.values())
    results = {tid: aggregate.aggregate(t, reps, NOW, 7, spots) for tid, t in targets.items()}
    export.export_targets(data_dir, tl)
    export.export_shards(data_dir, tl, results, NOW)
    (tmp_path / "index.html").write_text(
        (ROOT / "site" / "index.html").read_text(encoding="utf-8"), encoding="utf-8"
    )
    return Settings(
        _env_file=None,
        site_data_dir=data_dir,
        spots_path=ROOT / "data" / "spots.yaml",
        history_dir=tmp_path / "history",
        site_url=SITE_URL,
    )


def read(settings, rel):
    return (settings.site_data_dir.parent / rel).read_text(encoding="utf-8")


def test_spot_page_states_status_in_each_language(site):
    pages.write_pages(site)
    en = read(site, "spots/arashiyama/index.html")
    assert "Arashiyama: autumn leaves Peak as of" in en
    assert f'<link rel="canonical" href="{SITE_URL}/spots/arashiyama/">' in en
    ja = read(site, "ja/spots/arashiyama/index.html")
    assert "<h1>嵐山</h1>" in ja and "「見頃」" in ja
    assert '<html lang="ja">' in ja
    ko = read(site, "ko/spots/arashiyama/index.html")
    assert "&#x27;절정&#x27;" in ko and 'hreflang="zh-TW"' in ko
    # Directions search the spot by name, like the app.
    assert "destination=%E5%B5%90%E5%B1%B1%2C%20JP" in en


def test_untrusted_text_is_escaped(site):
    pages.write_pages(site)
    en = read(site, "spots/arashiyama/index.html")
    assert "<script>alert(1)" not in en
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in en


def test_language_homes_preset_their_language(site):
    pages.write_pages(site)
    root = read(site, "index.html")
    assert '<html lang="en">' in root  # the root follows the visitor's own preference
    assert read(site, "ja/index.html").count('<html lang="ja" data-lang="ja">') == 1
    ja_home = read(site, "ja/index.html")
    assert "<title>Peak Season｜近くの紅葉・桜の見頃が今わかる</title>" in ja_home
    assert root.count("<!-- seo:start -->") == 1


def test_regeneration_is_stable(site):
    assert pages.write_pages(site)
    assert pages.write_pages(site) == []


def test_sitemap_lists_every_language_version(site):
    pages.write_pages(site)
    xml = read(site, "sitemap.xml")
    assert f"<loc>{SITE_URL}/zh-tw/spots/arashiyama/</loc>" in xml
    assert 'hreflang="x-default"' in xml
    locs = re.findall(r"<loc>([^<]+)</loc>", xml)
    assert len(locs) == len(set(locs))


def test_history_keeps_one_entry_per_day(site):
    assert pages.record_history(site)
    assert not pages.record_history(site)
    [day] = json.loads((site.history_dir / f"{NOW.year}.json").read_text()).values()
    assert day["arashiyama"]["maple"] == {"stage": "peak", "reports": 2}
