"""Record small, trimmed iNaturalist responses into tests/fixtures/ (dev only, run by hand).

    uv run python scripts/record_fixtures.py

Tests never call live APIs; they read these files. Only the fields the fetcher uses are kept.
"""

import json
import time
from pathlib import Path

import httpx

OUT = Path(__file__).resolve().parent.parent / "tests" / "fixtures"
API = "https://api.inaturalist.org/v1"
UA = {"User-Agent": "PeakSeason-dev/0.1 (fixture recorder; open-source hackathon)"}

# name, taxon names, bbox (minlng, minlat, maxlng, maxlat), d1, d2
AREAS = [
    ("inat_acer_toronto", ["Acer"], (-79.6, 43.55, -79.2, 43.85), "2026-09-30", "2026-10-09"),
    ("inat_acer_kyoto", ["Acer"], (135.6, 34.9, 135.9, 35.1), "2026-09-30", "2026-10-09"),
    ("inat_acer_seoul", ["Acer"], (126.8, 37.45, 127.15, 37.7), "2026-09-30", "2026-10-09"),
    (
        "inat_sakura_sydney",
        ["Prunus serrulata", "Prunus × yedoensis", "Prunus × subhirtella"],
        (150.6, -34.2, 151.4, -33.5),
        "2026-09-01",
        "2026-10-09",
    ),
]
OBS_KEYS = [
    "id", "uri", "location", "obscured", "geoprivacy", "taxon_geoprivacy",
    "positional_accuracy", "time_observed_at", "observed_on", "place_guess",
]  # fmt: skip


def get(client: httpx.Client, path: str, **params) -> dict:
    time.sleep(1.1)  # stay under 1 request/second
    r = client.get(f"{API}{path}", params=params)
    r.raise_for_status()
    return r.json()


def trim(obs: dict) -> dict:
    out = {k: obs.get(k) for k in OBS_KEYS}
    out["taxon"] = {"id": obs["taxon"]["id"], "name": obs["taxon"]["name"]}
    out["photos"] = [
        {k: p.get(k) for k in ("id", "url", "license_code", "attribution")} for p in obs["photos"]
    ]
    out["annotations"] = [
        {k: a.get(k) for k in ("controlled_attribute_id", "controlled_value_id", "vote_score")}
        for a in obs.get("annotations") or []
    ]
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with httpx.Client(headers=UA, timeout=30) as c:
        terms = get(c, "/controlled_terms")
        keep = {"Leaves", "Flowers and Fruits"}
        terms["results"] = [
            {"id": t["id"], "label": t["label"],
             "values": [{"id": v["id"], "label": v["label"]} for v in t["values"]]}
            for t in terms["results"] if t["label"] in keep
        ]  # fmt: skip
        (OUT / "controlled_terms.json").write_text(json.dumps(terms, ensure_ascii=False, indent=1))

        taxa: dict[str, dict] = {}
        for name, taxon_names, bbox, d1, d2 in AREAS:
            ids = []
            for tn in taxon_names:
                if tn not in taxa:
                    data = get(c, "/taxa", q=tn)
                    data["results"] = [
                        {k: t[k] for k in ("id", "name", "rank")} for t in data["results"][:5]
                    ]
                    taxa[tn] = data
                ids += [t["id"] for t in taxa[tn]["results"] if t["name"] == tn]
            data = get(
                c, "/observations", taxon_id=",".join(map(str, ids)), d1=d1, d2=d2,
                photos="true", per_page=30, order_by="id", order="asc",
                swlng=bbox[0], swlat=bbox[1], nelng=bbox[2], nelat=bbox[3],
            )  # fmt: skip
            results = [trim(o) for o in data["results"]]
            body = {"total_results": len(results), "per_page": 200, "results": results}
            (OUT / f"{name}.json").write_text(json.dumps(body, ensure_ascii=False, indent=1))
            print(name, len(results), "observations")
        (OUT / "taxa.json").write_text(json.dumps(taxa, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
