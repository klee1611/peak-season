"""Famous viewing spots (data/spots.yaml): naming, budget priority and SerpApi queries."""

import re
from pathlib import Path

import yaml
from pydantic import BaseModel

from peakseason import geo


class Spot(BaseModel):
    name: str
    local_name: str | None = None
    lat: float
    lng: float
    country: str
    lang: str  # BCP-47
    known_for: list[str]

    @property
    def id(self) -> str:
        return re.sub(r"[^a-z0-9]+", "-", self.name.lower()).strip("-")

    @property
    def cell(self) -> str:
        return geo.encode(self.lat, self.lng)

    def query_name(self) -> str:
        """Name in the spot's own language, for search templates."""
        return self.local_name or self.name


def load_spots(path: Path) -> list[Spot]:
    if not path.is_file():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    return [Spot.model_validate(s) for s in data]


def nearest_spot(spots: list[Spot], lat: float, lng: float, max_km: float) -> Spot | None:
    best, best_d = None, max_km
    for s in spots:
        d = geo.haversine_km(lat, lng, s.lat, s.lng)
        if d <= best_d:
            best, best_d = s, d
    return best
