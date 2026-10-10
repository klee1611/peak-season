# Peak Season: Design

Status: validated in brainstorming on 2026-10-09 (Fri evening, Toronto). Deadline: Oct 11, 11:59 PM PDT (Sun Oct 12, 2:59 AM Toronto).

CLAUDE.md is the product spec. This document records the decisions made on top of it and the agreed build order. Where they differ, this document wins, and CLAUDE.md has been updated to match.

## Understanding summary

- **What:** Peak Season, a static, mobile-first site that tells people near them where a seasonal nature moment (maples now; sakura wherever reports exist) is at its peak right now, with ranked place cards and Directions links.
- **Why:** an entry for the DEV Hacktoberfest Open-Source AI Challenge, Week 1 "Touch Grass", aiming at Overall, Gemma, SerpApi, and GitHub Copilot. Long term, a global project that runs at $0/month.
- **Who:** anyone, anywhere, deciding whether to go out this weekend to see leaves or blossoms.
- **How:** a GitHub Actions job every 12 h pulls iNaturalist (plus SerpApi for famous spots); Gemma on CPU via Ollama classifies stages; the job exports sharded JSON that Cloudflare Pages serves as static files.
- **Scope:** the full CLAUDE.md plan: maple plus validated sakura plus SerpApi. Events only if milestone 4 is green by Sat 20:00.
- **Constraints:** no backend, no paid services, no scraping, no rehosted images, no hardcoded regions, no secrets in the repo, nothing in production depends on the developer's laptop.
- **Non-goals:** accounts, uploads, translated UI, map tiles, push notifications, fine-tuning.

## Assumptions (non-functional)

1. **Performance:** each shard is ≤200 KB gzipped (hard limit 300 KB raw, enforced in export). The first card renders in ≤2 s on 4G. Ingest finishes in ≤120 min, guaranteed by `CLASSIFY_DEADLINE_MIN`.
2. **Scale:** any amount of traffic (static files only). Data is a few hundred to a few thousand cells. About 60 Pages builds/month, against a free limit of 500.
3. **Privacy:** no cookies, analytics, or third-party scripts. Geolocation is used only in the browser. Only CC or public-domain photos show thumbnails; others appear as a link only.
4. **Reliability:** best effort. A failed run leaves the last good data live. "Last updated" tells users how fresh the data is.
5. **Maintenance:** single owner. The only recurring task is re-enabling the scheduled workflow if GitHub disables it after 60 days.
6. **Validation threshold:** a plant goes live only with ≥70% coarse-stage agreement with iNaturalist annotations on ≥20 photos.
7. **Accounts:** the developer creates them fresh (none exist yet) in this order: Ollama + uv (Fri), GitHub public repo (Sat AM), SerpApi (Sat PM), Cloudflare (Sat AM).

## Open questions (to check during the build)

- Does the iNaturalist "Leaves → Colored leaves" annotation exist? What are its term/value IDs (`/v1/controlled_terms`)?
- Which iNaturalist names resolve for ornamental cherries (*Prunus × yedoensis* or *Cerasus*?)
- Is a newer multimodal Gemma than `gemma3:4b` available in the Ollama library?
- What is the real CPU latency per photo on `ubuntu-latest`?
- Coordinates for about 25 famous spots: verify each one; flag the unsure ones `# TODO verify`.

## Decision log

| # | Decision | Alternatives considered | Why |
|---|---|---|---|
| 1 | Full scope; events only if ahead | Maple only; maple + SerpApi | Developer wants the most prize categories covered |
| 2 | Ingest every 12 h | 6 h; 2 days (original) | About 4× the coverage of 2 days (≥2 reports per cell needed); moderate commit noise |
| 3 | If CPU is too slow: shrink work, stay self-hosted | Hosted Gemma endpoint; decide later | Keeps the self-hosted / photos-never-leave / $0 story for Gemma and the write-up |
| 4 | Validate prompts against iNaturalist annotations (coarse groups) | Throwaway labelling page; spreadsheet | No developer time; limitation documented honestly in NOTES.md |
| 5 | All accounts created fresh, in the order needed | — | Nothing exists yet |
| 6 | Build order: thin end-to-end slice first, then widen | Layer by layer; site first | CPU-latency and deployment risk show up by Sat morning; always demoable |
| 7 | Annotation-only reports count as in-season signals and classification priority, **not** stage | Annotation → middle stage of its group | Mapping "colored leaves" to `peak` would invent `go_now` statuses |
| 8 | `CLASSIFY_DEADLINE_MIN` (default 90) in addition to `MAX_PHOTOS_PER_RUN` | Photo cap only | Run always finishes export and commit within the 120-min timeout |
| 9 | `validated: true` in target YAML gates UI visibility | Hidden list in code | Gate stays config-only; set by hand after `validate.py` passes |
| 10 | `site/data/run_stats.json` per run | Logs only | Real numbers for NOTES.md and the post, for free |
| 11 | iNaturalist `medium` (~500 px) image for both thumbnail and Gemma input, in memory only | Original size | Faster CPU inference; never stored or rehosted |
| 12 | Separate `ci.yml` (pytest + ruff) | Tests only locally | Shows quality; supports the Copilot/Actions angle |
| 13 | `in_season_signals` field in shards | Only `report_count` | Lets "Not enough reports" cards still say truthfully that sightings exist |
| 14 | Deterministic export (sorted keys, rounded coordinates) | — | No-change runs produce no diff and no commit |

## §1 Ingest pipeline

```
load targets/*.yaml + data/spots.yaml
  → resolve taxa (/v1/taxa) + annotation term IDs (/v1/controlled_terms), cached in SQLite
  → FETCH     iNat per target, last 10 days, photos=true, paged with id_above, ≤1 req/s
  → NORMALIZE Report(source, target_id, lat, lng, cell, observed_at, photo_url,
                     license, attribution, link, place_guess, kind=photo|annotation|text)
  → SIGNAL    matching annotation → in-season signal + priority boost (no model call, no stage)
  → BUDGET    famous-spot cells → busiest cells → rest; ≤MAX_PHOTOS_PER_CELL per (cell, target);
              stop at MAX_PHOTOS_PER_RUN or CLASSIFY_DEADLINE_MIN
  → CLASSIFY  Gemma via OpenAI-compatible client; cache key = sha256(photo_url + target + prompt_version)
  → SERPAPI   in-season famous spots with <3 reports only; Account API gate first
  → AGGREGATE per (cell, target), pure functions
  → EXPORT    targets.json, index.json, shards/<gh2>.json, run_stats.json
```

A taxon or annotation term that doesn't resolve is logged and skipped. A target with no resolved taxa is skipped for the run.

## §2 Model tasks, caching, failures

- `ModelClient` (httpx) → `POST {MODEL_BASE_URL}/chat/completions`, `response_format: json_object`, `temperature: 0`, images as base64 data URLs. Tests use a fake client.
- Prompts in `prompts/`, each starting with `# version: N`. The version is part of the cache key. Stage IDs and labels are filled in from the target YAML.
- Output is validated with Pydantic against the target's stage IDs. On invalid output, retry once with a JSON-only reminder; on a second failure, cache as `unclassified`. `is_target_photo: false` is cached as a rejection.
- Timeouts: model 180 s per call; iNaturalist/SerpApi 30 s with 3 retries (backoff 1/2/4 s). One log line per call (source, status, latency); never log secrets.
- `python -m peakseason.validate --target <id>`: about 25 annotated, CC-licensed archive photos. It reports coarse-group agreement (maple: Green leaves ↔ `green`, Colored leaves ↔ `turning|peak|past_peak`; sakura: Flower budding ↔ `buds`, Flowering ↔ `first_bloom|full_bloom`) and is-target rate. Results go in NOTES.md; then set `validated: true` by hand.

## §3 Aggregation and JSON contract

- `w = confidence × kind_weight × exp(-age_days / 3)`; photo 1.0, text 0.6; annotation-only reports carry no stage weight.
- Stage = weighted mean of stage indexes → nearest stage. Fewer than 2 stage-bearing reports → `not_enough_reports`.
- Coordinates: the famous spot's if one is in the cell, otherwise the median of the reports. Name: most common cleaned `place_guess` → nearest spot within 10 km → "Near <city>".
- Evidence: top 3 by recency then confidence; thumbnail only if the license allows display.

Shard example (`site/data/shards/dp.json`):

```json
{ "schema_version": 1, "generated_at": "2026-10-10T14:07:00Z", "geohash2": "dp",
  "targets": { "maple": [ {
      "cell": "dpz83", "name": "High Park", "lat": 43.6465, "lng": -79.4637,
      "stage": "peak", "report_count": 9, "in_season_signals": 14,
      "latest_report_at": "2026-10-10T11:20:00Z", "is_famous_spot": true,
      "evidence": [ { "link": "https://www.inaturalist.org/observations/…", "source": "inaturalist",
                      "thumb": "https://inaturalist-open-data.s3…/medium.jpg",
                      "license": "CC-BY-NC", "attribution": "(c) user, some rights reserved (CC BY-NC)",
                      "taken_at": "2026-10-09" } ] } ] } }
```

- `index.json`: `{ schema_version, generated_at, shards: { "<gh2>": { "go_now": [...], "in_season": [...] } } }`
- `targets.json`: stages, labels, `go_now` flags, local names, `validated`.
- Deterministic output; coordinates rounded to 4 decimals; cells with no reports in the window are dropped; run fails if a shard is over 300 KB.

## §4 Site

- Fetch `targets.json` and `index.json` → geolocation (8 s timeout; on decline, a city picker remembered in localStorage inside try/catch) → user's gh2 → load that shard plus existing neighbours (≤9) → filter by radius (50/100/250 km, default 100).
- Plant chips: validated targets with nearby cells; default is the one with the most `go_now` cells nearby.
- Cards sorted by `go_now` first, then stage progress, then `not_enough_reports`, then distance. Each card has a stage badge (text plus colour), distance (km/mi toggle), report count and how recent, one attributed thumbnail, source links, and Google/Apple/OSM Directions buttons.
- Top line from the best card; "Go this weekend" only if the newest report is under 3 days old, otherwise "Worth a look".
- Nothing nearby → say so, and point to the nearest gh2 region with `go_now` from `index.json`.
- All strings in `I18N.en` with a `t(key, vars)` helper; `Intl` for numbers and relative times. "Last updated" from `generated_at`.
- No third-party scripts or fonts; `textContent` only; lazy images with `referrerpolicy="no-referrer"`; mobile-first; dark mode via `prefers-color-scheme`.
- Dev: `?fixtures=1` loads `site/data/fixtures/` (Toronto, Kyoto, Sydney); `?lat=&lng=` overrides location.

## §5 Workflows and deployment

`ingest.yml`:
- Triggers: `cron: "17 4,16 * * *"` plus `workflow_dispatch` (optional `target`, `bbox`).
- Settings: `concurrency: ingest` (no cancel); `permissions: contents: write`; `timeout-minutes: 120`.
- Setup: checkout → setup-uv (Py 3.12) → `uv sync --frozen` → install Ollama → `actions/cache` `~/.ollama/models` keyed `ollama-${MODEL_NAME}` (pull on miss) → `ollama serve &` plus health check (fail after 60 s) → warm-up call.
- DB cache: `actions/cache/restore` key `db-${run_id}`, restore-keys `db-`.
- Run and commit: run ingest → commit `site/data/` only if changed, as `github-actions[bot]` → `actions/cache/save` (`if: always()`).
- Exits 0 without committing if no target has recent reports.

`ci.yml`: pytest, `ruff check`, `ruff format --check` on push and PR.

Cloudflare Pages:
- Git integration: branch `main`, no build command, output `site`.
- Commits by the workflow's bot token still trigger the Pages deploy.
- `site/_headers`: `/data/*` gets `Cache-Control: max-age=300`.

## §6 Testing

- **Fixtures** (recorded and trimmed; never live in tests): Acer from Toronto, Kyoto, and Seoul; *Prunus* ornamentals from Sydney; taxa, controlled_terms, SerpApi account, and a Japanese SerpApi search.
- **Unit:**
  - targets schema
  - geo (encode/neighbours including antimeridian and southern latitudes, haversine, Unicode place cleaning)
  - aggregate (both stage lists, both hemispheres, decay, <2 reports, annotation-has-no-stage, evidence and licensing)
  - budget (per-cell cap, priority, photo and time stops)
  - SerpApi gate (Account API unreachable, reserve, 48 h cache, per-run cap, no key)
  - model (valid, retry, unclassified, unknown stage, cache hit)
  - export (schema, deterministic bytes, size limit)
  - iNaturalist fetcher (id_above paging, obscured/missing coordinates, licenses)
- **Integration:** full ingest on fixtures with the fake model, compared against a stored golden output.
- **Site:** Playwright smoke test for Toronto, Kyoto, and Sydney in fixtures mode (cards, Directions coordinates, km/mi, nothing-nearby, no requests leaving the origin except thumbnails); it also produces the post's screenshots.
- **Manual:** `validate.py`, one test run via `workflow_dispatch` with a bbox, one global run.

## §7 Timeline (Toronto time) and risks

| When | Goal | Done when |
|---|---|---|
| Fri night | Scaffold, config, targets, geo, store, iNaturalist fetcher plus fixtures. Crude maple slice for Toronto running locally. *Dev: install uv and Ollama, pull `gemma3:4b`.* | Tests pass; local site shows a real Toronto card |
| Sat ≤10:00 | *Dev: public repo, Cloudflare.* ingest.yml plus ci.yml, test run with a bbox, Pages live, CPU latency measured, `MAX_PHOTOS_PER_RUN` set | Public URL shows data from Actions |
| Sat ≤14:00 | Global paging, budget, signals, time limit, run_stats, full UI, chips, nothing-nearby path, fixtures mode | Global run finishes under 120 min |
| Sat ≤18:00 | Sakura taxa plus prompt, validate both plants, *dev: SerpApi key secret*, SerpApi with gate and cache | Both plants validated; SerpApi within budget |
| Sat evening | Verified spots.yaml, Playwright plus 4-city screenshots, 12 h schedule on. Events only if all green by 20:00 | Second scheduled run commits by itself |
| Sun | README ("What's next", 60-day note), NOTES.md numbers, DEV post (developer writes; Claude reviews and fact-checks), park visit | Post published by Sun 23:00 (4 h slack) |

Risks:
- **Very slow CPU:** fewer photos per run, more reliance on signals.
- **Sakura fails validation:** stays hidden, and the post explains the gate.
- **Taxon name differences:** resolved at runtime.
- **Pages or Actions setup problems:** handled Saturday morning.
- **Write-up quality decides the result:** it gets its own day, and run_stats provides the numbers.
