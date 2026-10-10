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
