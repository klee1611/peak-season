"""Ingest runner: fetch -> normalize -> classify (budgeted) -> aggregate -> export.

uv run python -m peakseason.ingest
uv run python -m peakseason.ingest --target maple --bbox "-80,43,-79,44"
"""

import argparse
import asyncio
import logging
import statistics
import sys
import time
from datetime import UTC, datetime, timedelta

import httpx

from peakseason import aggregate, export
from peakseason.config import ROOT, Settings, get_settings
from peakseason.ingest import budget, serpapi
from peakseason.ingest.inaturalist import INatClient, normalize
from peakseason.model.classify import Classifier
from peakseason.model.client import ChatModel, OpenAICompatModel
from peakseason.reports import Report
from peakseason.spots import load_spots
from peakseason.store import Classification, Store
from peakseason.targets import Target, load_targets

log = logging.getLogger("peakseason.ingest")


def apply(report: Report, c: Classification) -> None:
    if c.status == "ok":
        report.stage, report.confidence = c.stage, c.confidence


def parse_bbox(text: str | None) -> tuple[float, float, float, float] | None:
    if not text:
        return None
    parts = [float(x) for x in text.split(",")]
    if len(parts) != 4:
        raise argparse.ArgumentTypeError("bbox must be minlng,minlat,maxlng,maxlat")
    return parts[0], parts[1], parts[2], parts[3]


async def fetch_reports(
    inat: INatClient, targets: list[Target], since, bbox, stats: dict
) -> tuple[list[Target], list[Report]]:
    terms = await inat.controlled_terms()
    active, reports = [], []
    for t in targets:
        ids = await inat.resolve_taxa(t)
        if not ids:
            log.warning("%s: no taxa resolved, skipping this run", t.id)
            continue
        active.append(t)
        fetched = 0
        for obs in [o async for o in inat.observations(ids, since, bbox)]:
            fetched += 1
            if (r := normalize(obs, t, terms)) is not None:
                reports.append(r)
        mine = [r for r in reports if r.target_id == t.id]
        stats["targets"][t.id] = {
            "observations_fetched": fetched,
            "reports_usable": len(mine),
            "with_displayable_photo": sum(r.photo_url is not None for r in mine),
            "annotation_signals": sum(r.in_season_signal for r in mine),
            "cells_seen": len({r.cell for r in mine}),
        }
        log.info("%s: %s", t.id, stats["targets"][t.id])
    return active, reports


async def classify_budgeted(
    classifier: Classifier,
    targets: list[Target],
    reports: list[Report],
    famous_cells: set[tuple[str, str]],
    settings: Settings,
    stats: dict,
    now: datetime,
) -> None:
    tmap = {t.id: t for t in targets}
    # Fetching reaches back further than the aggregation window (late uploads), but a photo
    # older than the window can never affect a card, so it is not worth a model call.
    window_start = now - timedelta(days=settings.window_days)
    candidates = []
    for r in reports:
        if r.photo_url is None:
            continue
        cached = classifier.cached_photo(tmap[r.target_id], r.photo_url)
        if cached is not None:
            apply(r, cached)
        elif r.observed_at >= window_start:
            candidates.append(r)

    chosen = budget.plan(
        candidates, famous_cells, settings.max_photos_per_run, settings.max_photos_per_cell
    )
    reserve = settings.text_reserve_min if settings.serpapi_api_key else 0
    deadline = time.monotonic() + (settings.classify_deadline_min - reserve) * 60
    done = 0
    for r in chosen:
        if time.monotonic() > deadline:
            log.warning("classification deadline reached after %d photos", done)
            break
        try:
            c = await classifier.classify_photo(tmap[r.target_id], r.photo_url)
        except httpx.HTTPError as exc:
            log.warning("could not fetch photo %s: %s", r.photo_url, exc)
            continue
        apply(r, c)
        done += 1

    lat = classifier.latencies
    stats["classification"] = {
        "candidates_uncached": len(candidates),
        "planned": len(chosen),
        "classified_this_run": done,
        "skipped_for_next_run": len(candidates) - done,
        "cells_classified_this_run": len({(r.cell, r.target_id) for r in chosen[:done]}),
        "latency_s_median": round(statistics.median(lat), 2) if lat else None,
        "latency_s_max": round(max(lat), 2) if lat else None,
    }
    log.info("classification: %s", stats["classification"])


async def extract_texts(
    classifier: Classifier,
    targets: list[Target],
    texts: list[Report],
    deadline: float,
    stats: dict,
) -> None:
    tmap = {t.id: t for t in targets}
    for done, r in enumerate(texts):
        if time.monotonic() > deadline:
            log.warning("deadline reached; %d text reports left for next run", len(texts) - done)
            break
        c = await classifier.extract_text(tmap[r.target_id], r.item_id, r.place_guess, r.text)
        apply(r, c)
    stats.setdefault("serpapi", {})["text_reports"] = len(texts)
    stats["serpapi"]["text_reports_with_stage"] = sum(r.stage is not None for r in texts)


async def run(
    settings: Settings,
    target_filter: str | None = None,
    bbox=None,
    now: datetime | None = None,
    model: ChatModel | None = None,
    http_transport: httpx.AsyncBaseTransport | None = None,
) -> int:
    started = time.monotonic()
    now = now or datetime.now(UTC)
    all_targets = load_targets(settings.targets_dir)
    targets = [t for t in all_targets if not target_filter or t.id == target_filter]
    spots = load_spots(settings.spots_path)
    store = Store(settings.sqlite_path)
    stats: dict = {"started_at": export.iso(now), "model": settings.model_name, "targets": {}}

    headers = {"User-Agent": settings.inat_user_agent}
    async with (
        httpx.AsyncClient(timeout=30, headers=headers, transport=http_transport) as http,
        httpx.AsyncClient(timeout=settings.model_timeout_s, transport=http_transport) as mhttp,
    ):
        inat = INatClient(http, store)
        since = (now - timedelta(days=settings.fetch_days)).date()
        targets, reports = await fetch_reports(inat, targets, since, bbox, stats)

        if model is None:
            model = OpenAICompatModel(
                mhttp, settings.model_base_url, settings.model_name, settings.model_api_key
            )
        classifier = Classifier(model, store, http, ROOT)
        famous = {(s.cell, tid) for s in spots for tid in s.known_for}
        await classify_budgeted(classifier, targets, reports, famous, settings, stats, now)

        # SerpApi runs after photo classification so "under-reported" counts Gemma's results.
        planned = serpapi.plan_queries(targets, spots, reports, now, settings.window_days)
        texts = await serpapi.SerpApiClient(http, store, settings).fetch(planned, stats)
        deadline = started + settings.classify_deadline_min * 60
        await extract_texts(classifier, targets, texts, deadline, stats)
        reports += texts

    results = {
        t.id: aggregate.aggregate(t, reports, now, settings.window_days, spots) for t in targets
    }
    for t in targets:
        cells = results[t.id]
        stats["targets"][t.id].update(
            cells_exported=len(cells),
            cells_with_stage=sum(c.stage is not None for c in cells),
            go_now_cells=sum(bool(c.stage and t.is_go_now(c.stage)) for c in cells),
        )

    if not any(results.values()):
        log.info("no target has recent reports anywhere; nothing to export")
        store.close()
        return 0

    covered_ids = set(results)

    def keep_existing(target_id: str, cell: dict) -> bool:
        """Keep cells outside this run's scope (other targets, or outside the dev bbox)."""
        if target_id not in covered_ids:
            return True
        return bbox is not None and not (
            bbox[0] <= cell["lng"] <= bbox[2] and bbox[1] <= cell["lat"] <= bbox[3]
        )

    out = settings.site_data_dir
    changed = {"targets.json": export.export_targets(out, all_targets)}
    changed.update(export.export_shards(out, all_targets, results, now, keep_existing))
    stats["files_changed"] = sorted(k for k, v in changed.items() if v)
    stats["duration_s"] = round(time.monotonic() - started, 1)
    export.export_run_stats(out, stats)
    log.info("exported; changed: %s", stats["files_changed"])
    store.close()
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="peakseason.ingest")
    p.add_argument("--target", help="only this target id")
    p.add_argument("--bbox", type=parse_bbox, help='dev: "minlng,minlat,maxlng,maxlat"')
    p.add_argument("--max-photos", type=int, help="override MAX_PHOTOS_PER_RUN")
    argv = list(sys.argv[1:] if argv is None else argv)
    # argparse treats "-80,43,-79,44" as a flag; glue it to --bbox so the documented
    # form `--bbox "-80,43,-79,44"` works.
    if "--bbox" in argv and (i := argv.index("--bbox")) + 1 < len(argv):
        argv[i : i + 2] = [f"--bbox={argv[i + 1]}"]
    args = p.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    settings = get_settings()
    if args.max_photos is not None:
        settings.max_photos_per_run = args.max_photos
    return asyncio.run(run(settings, args.target, args.bbox))


if __name__ == "__main__":
    sys.exit(main())
