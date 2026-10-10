"""Write site/data/: targets.json, index.json, shards/<geohash2>.json, run_stats.json.

This is the contract between ingest and the site. Output is deterministic (sorted keys,
rounded coordinates), and a file is only rewritten when its content (ignoring
`generated_at`) changed, so a run with nothing new produces no diff and no commit.
"""

import json
import logging
from collections import defaultdict
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from peakseason import geo
from peakseason.aggregate import CellResult
from peakseason.targets import Target

log = logging.getLogger("peakseason.export")

SCHEMA_VERSION = 1
MAX_SHARD_BYTES = 300_000


def iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def cell_json(c: CellResult) -> dict:
    return {
        "cell": c.cell,
        "name": c.name,
        "lat": round(c.lat, 4),
        "lng": round(c.lng, 4),
        "stage": c.stage or "not_enough_reports",
        "report_count": c.report_count,
        "in_season_signals": c.in_season_signals,
        "latest_report_at": iso(c.latest_report_at),
        "is_famous_spot": c.is_famous_spot,
        "evidence": [
            {
                "link": r.link,
                "source": r.source,
                "kind": r.kind,
                "stage": r.stage,
                "thumb": r.photo_url,
                "license": r.license,
                "attribution": r.attribution,
                "title": r.title,
                "taken_at": iso(r.observed_at),
            }
            for r in c.evidence
        ],
    }


def _dump(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"


def write_if_changed(path: Path, data: dict) -> bool:
    """Write `data` unless the existing file has the same content apart from generated_at."""
    if path.is_file():
        try:
            old = json.loads(path.read_text(encoding="utf-8"))
            old.pop("generated_at", None)
            new = {k: v for k, v in data.items() if k != "generated_at"}
            if old == json.loads(_dump(new)):
                return False
        except (json.JSONDecodeError, OSError):
            pass
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_dump(data), encoding="utf-8")
    return True


def export_targets(out: Path, targets: list[Target]) -> bool:
    data = {
        "schema_version": SCHEMA_VERSION,
        "targets": [
            {
                "id": t.id,
                "display_name": t.display_name,
                "local_names": t.local_names,
                "stages": [s.model_dump() for s in t.stages],
                "validated": t.validated,
            }
            for t in targets
        ],
    }
    return write_if_changed(out / "targets.json", data)


def existing_cells(out: Path) -> dict[str, list[dict]]:
    """target_id -> cells currently exported, read back from the shards on disk."""
    cells: dict[str, list[dict]] = defaultdict(list)
    for p in sorted((out / "shards").glob("*.json")):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        for tid, items in (data.get("targets") or {}).items():
            cells[tid].extend(items)
    return cells


def export_shards(
    out: Path,
    targets: list[Target],
    results: dict[str, list[CellResult]],
    now: datetime,
    keep_existing: Callable[[str, dict], bool] | None = None,
) -> dict[str, bool]:
    """Write one shard per geohash-2 region with data, plus index.json. Returns changed files.

    `keep_existing(target_id, cell)` keeps already-exported cells this run did not cover (a
    run limited to one target or a bbox must not wipe everything else).
    """
    tmap = {t.id: t for t in targets}
    per_target: dict[str, list[dict]] = defaultdict(list)
    for target_id, cells in results.items():
        per_target[target_id] += [cell_json(c) for c in cells]
    if keep_existing:
        for tid, cells in existing_cells(out).items():
            fresh = {c["cell"] for c in per_target[tid]}  # this run's result wins
            if tid in tmap:
                per_target[tid] += [
                    c for c in cells if c["cell"] not in fresh and keep_existing(tid, c)
                ]

    by_shard: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    go_now: dict[str, set[str]] = defaultdict(set)
    for target_id, cells in per_target.items():
        for c in sorted(cells, key=lambda c: c["cell"]):
            shard = c["cell"][: geo.SHARD_PRECISION]
            by_shard[shard][target_id].append(c)
            if tmap[target_id].is_go_now(c["stage"]):
                go_now[shard].add(target_id)

    changed: dict[str, bool] = {}
    shard_dir = out / "shards"
    for shard, per_target in sorted(by_shard.items()):
        data = {
            "schema_version": SCHEMA_VERSION,
            "generated_at": iso(now),
            "geohash2": shard,
            "targets": {tid: cells for tid, cells in sorted(per_target.items())},
        }
        size = len(_dump(data).encode())
        if size > MAX_SHARD_BYTES:
            raise ValueError(f"shard {shard} is {size} bytes (limit {MAX_SHARD_BYTES})")
        changed[f"shards/{shard}.json"] = write_if_changed(shard_dir / f"{shard}.json", data)

    # Remove shards that no longer have any data.
    if shard_dir.is_dir():
        for p in shard_dir.glob("*.json"):
            if p.stem not in by_shard:
                p.unlink()
                changed[f"shards/{p.name}"] = True

    index = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": iso(now),
        "shards": {
            shard: {
                "go_now": sorted(go_now[shard]),
                "in_season": sorted(per_target),
                "cells": sum(len(v) for v in per_target.values()),
            }
            for shard, per_target in sorted(by_shard.items())
        },
    }
    changed["index.json"] = write_if_changed(out / "index.json", index)
    return changed


def export_run_stats(out: Path, stats: dict) -> None:
    out.mkdir(parents=True, exist_ok=True)
    (out / "run_stats.json").write_text(
        json.dumps(stats, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
