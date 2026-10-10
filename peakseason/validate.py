"""Check a target's photo prompt against iNaturalist phenology annotations before it goes live.

    uv run python -m peakseason.validate --target maple [--per-group 13]

Annotations only give coarse groups (e.g. maple "Colored Leaves" spans turning..past_peak),
so this measures coarse-stage agreement, not exact stages. A target goes live only with
>= 70% agreement on >= 20 photos; then set `validated: true` in its YAML by hand and record the
printed Markdown in NOTES.md.
"""

import argparse
import asyncio
import logging
import sys
from datetime import UTC, datetime

import httpx

from peakseason.config import ROOT, get_settings
from peakseason.ingest.inaturalist import DISPLAYABLE_LICENSES, INatClient, normalize
from peakseason.model.classify import Classifier
from peakseason.model.client import OpenAICompatModel
from peakseason.store import Store
from peakseason.targets import Target, load_targets

log = logging.getLogger("peakseason.validate")

PASS_AGREEMENT = 0.70
MIN_PHOTOS = 20


async def sample(
    inat: INatClient, target: Target, per_group: int, until: str | None = None
) -> list[tuple[str, dict]]:
    """(group label, observation) pairs: research-grade, annotated, displayable photos.

    Each observation appears once, under the group it was sampled for.
    """
    ann = target.inat_annotation
    if ann is None:
        raise SystemExit(f"{target.id}: no inat_annotation configured; cannot validate")
    terms = await inat.controlled_terms()
    term_id = next((i for i, (label, _) in terms.items() if label == ann.term), None)
    if term_id is None:
        raise SystemExit(f"annotation term {ann.term!r} not found in /v1/controlled_terms")
    values = {label: vid for vid, label in terms[term_id][1].items()}
    taxa = await inat.resolve_taxa(target)
    out = []
    seen: set[int] = set()
    for group in ann.validation_groups:
        if group not in values:
            raise SystemExit(f"annotation value {group!r} not found for term {ann.term!r}")
        data = await inat._get(
            "/observations",
            {
                "taxon_id": ",".join(map(str, taxa)),
                "term_id": term_id,
                "term_value_id": values[group],
                "photos": "true",
                "photo_license": ",".join(sorted(DISPLAYABLE_LICENSES)),
                "quality_grade": "research",
                "per_page": per_group * 2,  # some will be unusable after normalizing
                **({"d2": until} if until else {}),
            },
        )
        picked = 0
        for obs in data.get("results", []):
            r = normalize(obs, target, terms)
            if r and r.photo_url and picked < per_group and obs["id"] not in seen:
                seen.add(obs["id"])
                out.append((group, obs))
                picked += 1
    return out


def observed_groups(target: Target, labels: list[str]) -> set[str]:
    """Validation groups present among an observation's annotation labels ("Term=Value")."""
    ann = target.inat_annotation
    return {g for g in ann.validation_groups if f"{ann.term}={g}" in labels}


async def validate(target_id: str, per_group: int, until: str | None = None) -> int:
    settings = get_settings()
    target = next((t for t in load_targets(settings.targets_dir) if t.id == target_id), None)
    if target is None:
        raise SystemExit(f"unknown target {target_id!r}")
    store = Store(settings.sqlite_path)
    headers = {"User-Agent": settings.inat_user_agent}
    async with (
        httpx.AsyncClient(timeout=30, headers=headers) as http,
        httpx.AsyncClient(timeout=settings.model_timeout_s) as mhttp,
    ):
        inat = INatClient(http, store)
        pairs = await sample(inat, target, per_group, until)
        model = OpenAICompatModel(
            mhttp, settings.model_base_url, settings.model_name, settings.model_api_key
        )
        clf = Classifier(model, store, http, ROOT)
        terms = await inat.controlled_terms()
        rows = []
        for group, obs in pairs:
            r = normalize(obs, target, terms)
            c = await clf.classify_photo(target, r.photo_url)
            # One observation can carry several values ("Green Leaves" and "Colored Leaves" on a
            # half-turned tree); a stage that fits any of them agrees.
            groups = observed_groups(target, r.annotations) or {group}
            accepted = {st for g in groups for st in target.inat_annotation.validation_groups[g]}
            ok = c.status == "ok" and c.stage in accepted
            rows.append((" + ".join(sorted(groups)), c.status, c.stage, ok, r.link))
            log.info("%s -> %s %s %s", group, c.status, c.stage, "OK" if ok else "MISS")
    store.close()

    n = len(rows)
    agree = sum(ok for *_, ok, _ in rows)
    rejected = sum(status == "rejected" for _, status, *_ in rows)
    rate = agree / n if n else 0.0
    passed = n >= MIN_PHOTOS and rate >= PASS_AGREEMENT
    lat = clf.latencies
    print(f"\n### Validation: {target.id} ({datetime.now(UTC):%Y-%m-%d}, {settings.model_name})\n")
    held_out = f", observed on or before {until}" if until else ""
    print(f"- Photos: {n} (research grade, annotated, CC-licensed{held_out})")
    both = sum(" + " in g for g, *_ in rows)
    if both:
        single = [ok for g, _, _, ok, _ in rows if " + " not in g]
        print(
            f"- {both} photos carry several annotation values (any stage in them agrees); "
            f"without them: {sum(single)}/{len(single)} = {sum(single) / len(single):.0%}"
        )
    print(f"- Coarse-stage agreement: {agree}/{n} = {rate:.0%} (pass needs >= 70% on >= 20)")
    print(f"- Rejected as not showing the target: {rejected}")
    if lat:
        print(f"- Model latency: median {sorted(lat)[len(lat) // 2]:.1f}s, max {max(lat):.1f}s")
    print(f"- Result: **{'PASS' if passed else 'FAIL'}**\n")
    print("| Annotation | Model | Agrees | Observation |\n|---|---|---|---|")
    for group, status, stage, ok, link in rows:
        print(f"| {group} | {stage or status} | {'yes' if ok else 'no'} | {link} |")
    return 0 if passed else 1


def main() -> int:
    p = argparse.ArgumentParser(prog="peakseason.validate")
    p.add_argument("--target", required=True)
    p.add_argument("--per-group", type=int, default=13)
    p.add_argument("--until", help="only photos observed on or before this date (held-out set)")
    args = p.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    return asyncio.run(validate(args.target, args.per_group, args.until))


if __name__ == "__main__":
    sys.exit(main())
