"""Per-(cell, target) scoring. Pure, target-agnostic functions; no I/O.

Weight of a report: w = confidence * kind_weight * exp(-age_days / 3).
Stage = weighted mean of stage indexes, rounded to the nearest stage.
Fewer than MIN_REPORTS stage-bearing reports -> no stage ("Not enough reports"). Never invent one.
Annotation-only reports carry no stage: they only count as in-season signals.
"""

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from peakseason import geo
from peakseason.reports import Report
from peakseason.spots import Spot, nearest_spot
from peakseason.targets import Target

KIND_WEIGHT = {"photo": 1.0, "text": 0.6}
DECAY_DAYS = 3.0
MIN_REPORTS = 2
EVIDENCE_COUNT = 3
SPOT_NAME_RADIUS_KM = 10.0


@dataclass
class CellResult:
    cell: str
    target_id: str
    name: str | None
    lat: float
    lng: float
    stage: str | None  # None = not enough reports
    report_count: int
    in_season_signals: int
    latest_report_at: datetime | None
    is_famous_spot: bool
    # For a famous spot, Directions search its name: spots.yaml points can be area centroids,
    # and the map app knows where visitors actually go.
    directions_query: str | None = None
    evidence: list[Report] = field(default_factory=list)


def weight(report: Report, now: datetime) -> float:
    age_days = max(0.0, (now - report.observed_at).total_seconds() / 86400)
    return (report.confidence or 0.0) * KIND_WEIGHT[report.kind] * math.exp(-age_days / DECAY_DAYS)


def score_stage(target: Target, reports: list[Report], now: datetime) -> str | None:
    staged = [r for r in reports if r.stage is not None]
    if len(staged) < MIN_REPORTS:
        return None
    total = sum(weight(r, now) for r in staged)
    if total <= 0:
        return None
    mean = sum(weight(r, now) * target.stage_index(r.stage) for r in staged) / total
    # Round half up (Python's round() is banker's rounding, which would make ties depend
    # on whether the index is even). Exact ties are rare with real weights.
    index = min(len(target.stages) - 1, int(math.floor(mean + 0.5)))
    return target.stage_ids[index]


def pick_evidence(reports: list[Report]) -> list[Report]:
    usable = [r for r in reports if r.stage is not None]
    usable.sort(key=lambda r: (r.observed_at, r.confidence or 0), reverse=True)
    return usable[:EVIDENCE_COUNT]


def name_cell(reports: list[Report], spot: Spot | None, nearby: Spot | None) -> str | None:
    if spot:
        return spot.name
    guesses = [r.place_guess for r in reports if r.source == "inaturalist"]
    if name := geo.cell_name(guesses):
        return name
    if nearby:
        return nearby.name
    if city := geo.cell_city(guesses):
        return f"Near {city}"
    return None


def aggregate_cell(
    target: Target,
    cell: str,
    reports: list[Report],
    now: datetime,
    window_days: int,
    spots: list[Spot],
) -> CellResult | None:
    """Aggregate one (cell, target). Returns None if the cell has nothing worth showing."""
    since = now - timedelta(days=window_days)
    recent = [r for r in reports if r.cell == cell and r.target_id == target.id]
    recent = [r for r in recent if since <= r.observed_at <= now + timedelta(hours=1)]
    signals = [r for r in recent if r.stage is not None or r.in_season_signal]
    if not signals:
        return None

    spot = next((s for s in spots if s.cell == cell and target.id in s.known_for), None)
    if spot:
        lat, lng = spot.lat, spot.lng
    else:
        located = [r for r in recent if r.source == "inaturalist"] or recent
        lat = geo.median([r.lat for r in located])
        lng = geo.median([r.lng for r in located])
    nearby = None if spot else nearest_spot(spots, lat, lng, SPOT_NAME_RADIUS_KM)

    staged = [r for r in recent if r.stage is not None]
    return CellResult(
        cell=cell,
        target_id=target.id,
        name=name_cell(recent, spot, nearby),
        lat=lat,
        lng=lng,
        stage=score_stage(target, recent, now),
        report_count=len(staged),
        in_season_signals=len(signals),
        latest_report_at=max(r.observed_at for r in signals),
        is_famous_spot=spot is not None,
        directions_query=f"{spot.local_name or spot.name}, {spot.country}" if spot else None,
        evidence=pick_evidence(recent),
    )


def aggregate(
    target: Target, reports: list[Report], now: datetime, window_days: int, spots: list[Spot]
) -> list[CellResult]:
    cells = sorted({r.cell for r in reports if r.target_id == target.id})
    results = []
    for cell in cells:
        res = aggregate_cell(target, cell, reports, now, window_days, spots)
        if res is not None:
            results.append(res)
    return results
