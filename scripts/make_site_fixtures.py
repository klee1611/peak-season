"""Build site/data/fixtures/ for offline site testing (`?fixtures=1`), using the real exporter.

    uv run python scripts/make_site_fixtures.py

Observations, photos and attributions come from the recorded iNaturalist fixtures; the stages
are made up for testing (Toronto: maples at peak, Kyoto: turning, Sydney: sakura in bloom).
"""

import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

from peakseason import aggregate, export
from peakseason.config import ROOT
from peakseason.ingest.inaturalist import normalize
from peakseason.spots import load_spots
from peakseason.targets import load_targets

OUT = ROOT / "site" / "data" / "fixtures"
FIX = ROOT / "tests" / "fixtures"
NOW = datetime(2026, 10, 9, 23, 0, tzinfo=UTC)
STAGES = {
    "inat_acer_toronto": ("maple", ["peak", "peak", "turning"]),
    "inat_acer_kyoto": ("maple", ["turning", "green"]),
    "inat_acer_seoul": ("maple", ["turning", "peak"]),
    "inat_sakura_sydney": ("sakura", ["full_bloom", "first_bloom"]),
}


def main() -> None:
    targets = load_targets(ROOT / "targets")
    for t in targets:
        t.validated = True  # fixtures show every target
    tmap = {t.id: t for t in targets}
    reports = []
    for name, (tid, cycle) in STAGES.items():
        data = json.loads((FIX / f"{name}.json").read_text(encoding="utf-8"))
        for i, obs in enumerate(data["results"]):
            r = normalize(obs, tmap[tid], {})
            if r and r.photo_url:
                # Pretend everything is recent so cards show up at NOW.
                r.observed_at = NOW.replace(hour=12 - i % 10)
                r.stage, r.confidence = cycle[i % len(cycle)], 0.9
                reports.append(r)
    spots = load_spots(ROOT / "data" / "spots.yaml")
    results = {t.id: aggregate.aggregate(t, reports, NOW, 7, spots) for t in targets}
    shutil.rmtree(OUT, ignore_errors=True)
    export.export_targets(OUT, targets)
    export.export_shards(OUT, targets, results, NOW)
    for p in sorted(Path(OUT).rglob("*.json")):
        print(p.relative_to(ROOT), p.stat().st_size, "bytes")


if __name__ == "__main__":
    main()
