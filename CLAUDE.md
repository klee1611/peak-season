# Peak Season

Crowdsourced, AI-verified tracker for seasonal nature moments **anywhere in the world**: autumn leaves, cherry blossoms, and more. Peak Season automatically collects recent public photos and posts, uses a self-hosted open-weight model (Gemma) to judge how far along each moment is, and tells people near them where it's at its peak **right now**, so they go outside.

**Live at launch (October):** maples / autumn leaves across the northern hemisphere (North America, Europe, and East Asia, where *momiji* and *danpung* peak in October–November). Cherry blossoms are also configured, and may already show live data in the southern hemisphere's spring.

Built for the DEV **Hacktoberfest Open-Source AI Challenge, Week 1: "Touch Grass"**, and intended as a **long-term, global project that runs at $0/month**.

## Hard constraints (read first)

- **Deadline: Oct 11, 2026, 11:59 PM PDT (Sun Oct 12, 2:59 AM Toronto).** Scope ruthlessly. A working MVP beats a half-finished ambitious one.
- The repo must be created and completed within the challenge window (Oct 5–11). Any commit after the deadline must be noted in README.md.
- **Open-source AI must be the core**, not decoration. Photo classification and text understanding run on an open-weight model (Gemma) via Ollama, inside the GitHub Actions runner.
- **No dependency on the developer's machine.** Production runs entirely on free cloud services (GitHub Actions for ingest, Cloudflare Pages for hosting). The developer's laptop is only for writing code and local testing; nothing in production may require it to be on.
- **$0 running cost.** No paid hosting, no always-on servers, no managed databases. Every design choice must keep it that way.
- **Global by design.** Nothing may assume a country, hemisphere, language, or calendar season. No region is hardcoded.
- **No scraping of closed platforms** (Instagram, Facebook, X, TikTok, LINE, Weibo, etc.). Only official, documented APIs with terms that allow this use.
- **Never rehost third-party images.** Link to the original post. Display iNaturalist photos only with their license and attribution shown.
- Do not commit secrets. All keys come from environment variables.

## The product (MVP)

1. User opens the web page. It asks for their location (browser geolocation); if they decline, they pick from a short list of world cities (Toronto, New York, London, Tokyo, Kyoto, Seoul, Taipei, Sydney, ...).
2. The page shows the **plant(s) of the moment for their area**: targets with recent reports nearby, with the featured one (most `go_now` reports nearby) selected by default. If nothing is in season nearby, say so plainly and show the nearest region where something is.
3. A **ranked list of place cards** (no map), sorted by stage (`go_now` first) and then by straight-line distance computed in the browser. Each card shows: place name, stage badge (for maples: **Green / Turning / Peak / Past peak**, or **Not enough reports**), distance (km, with a km/mi toggle), number of recent reports and how recent, one evidence thumbnail with attribution, and links to the original photos/posts.
4. Every card has **"Directions" buttons** that open the user's own map app via free URL links (no API key, no cost):
   - Google Maps: `https://www.google.com/maps/dir/?api=1&destination=<lat>,<lng>`
   - Apple Maps: `https://maps.apple.com/?daddr=<lat>,<lng>`
   - OpenStreetMap: `https://www.openstreetmap.org/directions?to=<lat>,<lng>`
5. A one-line recommendation at the top, e.g. "Peak colour 40 km away at X. 9 reports in the last 3 days. Go this weekend."
6. A visible "Last updated" time, so users know how fresh the data is.

The screen should be the shortest part of the experience: decide, tap Directions, go. No feeds, no infinite scroll, no accounts. Mobile-first layout. UI text is English for the MVP, but all strings live in one dictionary in `app.js` so translations (Japanese, Korean, Traditional Chinese, ...) can be added later.

### Non-goals for MVP

- User accounts, uploads, or comments
- Any backend server or API in production
- Translated UI (structure for it only)
- Festivals and events as a standalone feature (see "Stretch goal: nearby outdoor events")
- Fine-tuning, mobile app, push notifications
- An interactive map with tiles (possible later with a free-tier tile provider; the list + directions links cover the need at $0)

## Architecture: static site + scheduled ingest on GitHub Actions

```
 ingest: scheduled GitHub Actions workflow (every 12 hours), fully automatic
 ┌────────────────────────────────────────────────────────────────────────────┐
 │ iNaturalist (global) ─┐                                                    │
 │ SerpApi (famous spots)┼─> fetch ─> normalize ─> classify (Gemma) ─> SQLite │
 │                       │                                      (cache/state) │
 │                       └─> cluster into cells ─> aggregate ─> export shards │
 └────────────────────────────────────────────────────────────────────────────┘
                                                              │ commit by workflow
                                                              ▼
   Cloudflare Pages: static HTML/JS loads only the user's regional shard and renders place cards
```

- **There is no production backend.** The website is static files only. All model calls, API calls, and aggregation happen in the ingest job, which exports precomputed JSON.
- Consequence: **visitors never trigger any API or model call.** Traffic costs nothing, however much there is.
- Every model call is cached in SQLite by content hash (photo URL or text + target id + prompt version), so re-runs never re-classify the same item.

### The ingest workflow (`.github/workflows/ingest.yml`)

- Triggers: `schedule` (every 12 hours, at an off-peak minute, not `:00`, e.g. `17 4,16 * * *`) and `workflow_dispatch` (manual run button).
- Steps: checkout → set up uv/Python → install Ollama → restore the Gemma model from `actions/cache` (pull only on a cache miss) → start `ollama serve` → restore the SQLite cache → run ingest → commit changed `site/data/` with a bot identity → save caches. Cloudflare Pages redeploys automatically from the new commit (Git integration).
- `timeout-minutes: 120`. Ingest must cap model work per run with `MAX_PHOTOS_PER_RUN` (default 80) and a wall-clock `CLASSIFY_DEADLINE_MIN` (default 90) so it always finishes export and commit; leftovers are picked up next run (see "Classification budget").
- Runners have **no GPU**: Gemma runs on CPU. Log per-photo latency. Default to the smallest multimodal Gemma that classifies acceptably; keep it configurable with `MODEL_NAME`.
- **Fallback / scaling path:** `MODEL_BASE_URL`/`MODEL_NAME` can point to a hosted Gemma endpoint (OpenAI-compatible) via repo secrets, with no code changes, if CPU capacity is not enough for global coverage.
- Secrets: `SERPAPI_API_KEY` (and later `TICKETMASTER_API_KEY`) as GitHub Actions secrets. Never echo them.
- Permissions: `contents: write` only. Concurrency group so two runs never overlap.
- If no target has any recent reports anywhere, the job exits early without committing.
- Note in README: GitHub disables scheduled workflows in public repos after 60 days without repository activity (it emails a warning first); re-enable from the Actions tab.
- **SQLite cache persistence:** the DB lives in `actions/cache` and may be evicted. Losing it must be harmless: it only causes re-classification. It must never be the source of truth for the SerpApi budget (see below).

## Locations: global cells + famous spots

You cannot hand-curate parks for the whole world, so locations are **derived from the data**:

- **Cells:** every report is assigned to a geohash cell at precision 5 (about 5 km × 5 km). Aggregation happens per (cell, target).
- **Cell name:** the most common normalized iNaturalist `place_guess` among the cell's reports (strip street addresses; keep park/area/city names). If none is usable, use the nearest famous spot within 10 km, else "Near <city>" from the most common place_guess city part.
- **Cell coordinates:** the median lat/lng of the cell's reports (so Directions lead to where photos were actually taken), unless a famous spot is in the cell, in which case use the spot's coordinates.
- **Famous spots:** a small curated list in `data/spots.yaml` of world-renowned viewing places, used for naming, priority in the classification budget, and SerpApi queries. Fields: `name`, `local_name`, `lat`, `lng`, `country`, `lang` (BCP-47, e.g. `ja`, `ko`, `zh-TW`, `en`), `known_for: [maple, sakura]`. Start with ~25 across Canada, the US, Europe, Japan, Korea, Taiwan, and Australia (e.g. High Park, Algonquin, Central Park, the Tidal Basin, Kew Gardens, Ueno Park, Arashiyama, Yeouido, Seoraksan, Yangmingshan, Alishan).
- **Coordinates must be verified**, not recalled from memory. Flag any entry you are unsure about with a `# TODO verify` comment for the developer.

## Seasonal targets (the core abstraction)

**Nothing in the code may be maple-specific.** Everything that differs between maples, cherry blossoms, etc. lives in one YAML file per target in `targets/`. Adding a new target must require only a new YAML file and a prompt file, with no code changes.

**Seasons are local, so "in season" is decided by data, not by calendar months.** A target is in season for a cell if it has recent reports there. The featured "plant of the moment" for a user is the in-season target with the most `go_now` reports in their area.

**Curated, not exhaustive.** Peak Season covers a small, hand-picked set of famous, photogenic seasonal moments, not every plant:
- Keep the total number of targets small (MVP: 2), so ingest time, SerpApi budget, and the UI stay small.
- A target never appears in the UI until its prompt has been validated on at least 20 sample photos with ≥70% coarse-stage agreement against iNaturalist phenology annotations (`python -m peakseason.validate --target <id>`; record results in NOTES.md), and `validated: true` is set by hand in its YAML.

Each target defines:

```yaml
id: maple
display_name: Autumn leaves (maples)
local_names: { ja: 紅葉, ko: 단풍, zh-TW: 楓葉 }   # for display and search phrasing
inat_taxa:                      # names resolved to IDs at runtime via /v1/taxa; never hardcode IDs
  - { name: Acer, rank: genus }
stages:                         # ordered; index = progress score
  - { id: green,     label: Green }
  - { id: turning,   label: Turning }
  - { id: peak,      label: Peak, go_now: true }
  - { id: past_peak, label: Past peak }
photo_prompt: prompts/maple_photo.txt
text_prompt: prompts/generic_text.txt
search_queries:                 # SerpApi templates per language; {place} = spot name in that language
  en: '"fall colours" "{place}"'
  ja: '"{place}" 紅葉 見頃'
  ko: '"{place}" 단풍'
  zh-TW: '"{place}" 楓葉'
inat_annotation: null           # optional phenology annotation to use as an extra signal
```

For this weekend:
- **`maple`:** fully implemented, tested, and published.
- **`sakura`** (cherry blossoms; stages: buds / first bloom / full bloom / falling petals, `go_now` on first bloom and full bloom): full config + prompt. **Do not use genus *Prunus*** (it includes plums and wild cherries); list ornamental flowering cherries as separate taxa, e.g. *Prunus serrulata*, *Prunus × yedoensis*, *Prunus subhirtella*, *Prunus campanulata* (Taiwan), *Prunus sargentii*. Confirm each name resolves in `/v1/taxa`. Validate the prompt on 20 archived spring photos. It goes live automatically wherever recent reports exist (e.g. the southern hemisphere in October).
- Other future ideas (do **not** build now; list them in README "What's next"): plum blossoms, tulips, lavender, sunflowers, tamaracks, ginkgo (yellow), lupins.

## Classification budget (global coverage on a free CPU)

A free runner cannot classify every photo in the world. Ingest must spend `MAX_PHOTOS_PER_RUN` wisely:

1. **Free signals first:** where iNaturalist observations carry a matching phenology annotation (e.g. flowering, coloured leaves), turn them into **in-season signals without a model call**: they mark the target as in season for the cell and move those photos to the front of the classification queue, but they **do not set a stage** ("coloured leaves" spans turning to past peak, so mapping it to a stage would invent statuses). Look up term/value IDs from `/v1/controlled_terms`; never guess them.
2. **Per-cell cap:** classify at most `MAX_PHOTOS_PER_CELL` (default 3) unclassified photos per (cell, target) per run, newest first. Three good photos per cell beat thirty in one cell.
3. **Priority order:** cells containing famous spots → cells with the most recent observations → the rest. Stop when the run budget is spent; the cache means the next run continues where this one stopped.
4. Log coverage per run (cells seen, cells classified, photos skipped) to NOTES.md-friendly output.

## Usage and cost rules

- **Gemma runs via Ollama on the free GitHub Actions runner**: no quota, no cost (public repo).
- **iNaturalist**: free, no key; stay at ≤1 request/second with a descriptive User-Agent. Query globally by taxon + date range + `photos=true`; paginate with `id_above` (deep page numbers are capped). Stay well under their recommended daily request volume.
- **SerpApi is optional, budgeted, and limited to famous spots.** The free plan is small (about 100 searches/month; check the account dashboard).
  - If `SERPAPI_API_KEY` is unset, ingest skips SerpApi and runs on iNaturalist alone, with a log line saying so.
  - Only query for famous spots where the target is currently in season (has recent iNaturalist reports nearby) but has fewer than 3 reports, using the query template in the spot's language.
  - Cache every response in SQLite keyed by (target, spot, query). **Do not re-query while the cached response is younger than `SERPAPI_CACHE_HOURS` (default 48).**
  - **Budget source of truth is SerpApi's Account API** (it reports this month's usage and searches left, and does not consume a search; confirm the endpoint in their docs). At the start of each run, read it and stop SerpApi calls if remaining searches would drop below `SERPAPI_RESERVE` (default 20). Also respect `SERPAPI_MAX_CALLS_PER_RUN` (default 10). If the Account API is unreachable, make zero SerpApi calls that run.
  - Also log calls in a `serpapi_usage` table for debugging, but never rely on it for the budget (the cache can be evicted).
- **Hosting**: Cloudflare Pages (free; unlimited static bandwidth, commercial use allowed). **Compute**: GitHub Actions (free for public repos). No paid services anywhere.

## Stack

- **Ingest:** Python 3.12, httpx (async), Pydantic v2, SQLite (stdlib `sqlite3`) for cache and state, a small geohash helper (write it or use a tiny pure-Python package).
- **Tooling:** uv for dependencies, ruff for lint and format, pytest.
- **Model:** Gemma (multimodal, multilingual) via Ollama. Default tag `gemma3:4b`; check the Ollama library for the newest multimodal Gemma and make the tag configurable via `MODEL_NAME`.
- **Model client:** talk to Ollama through its OpenAI-compatible endpoint so the provider can be swapped by changing `MODEL_BASE_URL`.
- **Site:** static `site/` folder: `index.html`, vanilla JS, CSS. No build step, no framework, no map library, no third-party scripts. Geohash encoding/neighbours and haversine distance are implemented in a few lines of JS. Navigation is handed off to the user's own map app via the directions URLs above.
- **Hosting:** Cloudflare Pages via Git integration: connect the GitHub repo, no build command, output directory `site`. Every commit to the main branch deploys automatically. The site is plain static files, so it can move to GitHub Pages, Netlify, or Vercel without code changes.
- **Scheduler/compute:** GitHub Actions (see "The ingest workflow").

## Data sources

### iNaturalist (primary, global)
- Public API: `https://api.inaturalist.org/v1/observations`. No key needed.
- Query recent observations (last ~10 days) of each target's taxa, worldwide, with photos.
- Keep only photos whose license allows display; store license code, attribution string, `place_guess`, coordinates, and `observed_on`. Skip observations with obscured or missing coordinates.
- Where a target has a matching phenology annotation, use it as a free signal (see "Classification budget").

### SerpApi (secondary, famous spots only)
- Follow "Usage and cost rules" strictly.
- Query per famous spot using the target's template for the spot's `lang`, restricted to the past week, with the matching Google language/region parameters.
- Use result titles/snippets as **text reports** for that spot; the model extracts the stage. Link to the source; do not download or rehost images.

## Model tasks

All prompts live in `prompts/` as versioned text files. All outputs must be **strict JSON**, validated with Pydantic against the target's stage list; on invalid output, retry once, then mark the item `unclassified`.

1. **Photo classification:** input image + target → `{ "is_target_photo": bool, "stage": <one of target's stage ids>, "progress": 0.0–1.0, "confidence": 0.0–1.0 }`. Reject photos that don't show the target (a selfie with no trees, a different species, fruit instead of blossoms).
2. **Text report extraction (any language):** input snippet + target → `{ "place": str | null, "stage": <stage id> | null, "confidence": 0.0–1.0 }`. Understand informal and local phrasing ("the trees are on fire" = peak; 満開 = full bloom; 見頃 = at its best; 단풍 절정 = peak).

## Aggregation (per cell, per target)

- Include reports from the last `WINDOW_DAYS` (default 7) in the cell. SerpApi text reports for a famous spot count for the spot's cell.
- Recency weight: `w = confidence * exp(-age_days / 3)`. Photos weigh 1.0, text reports 0.6. Annotation-only reports carry no stage weight; they are exported as `in_season_signals`.
- Stage score = the stage's index in the target's `stages` list. Weighted mean → nearest stage.
- If there are fewer than 2 reports, status is **"Not enough reports"**. Never invent a status.
- Return the top 3 evidence items (most recent, highest confidence) with links and attribution.
- Keep this logic pure, target-agnostic, and fully unit-tested (test with both maple and sakura stage lists, and with cells in both hemispheres).

## Exported JSON (the contract between ingest and site)

- `site/data/targets.json`: all targets with display names, local names, stages, and `schema_version`.
- `site/data/shards/<geohash2>.json`: one file per precision-2 geohash region (about 1,250 km × 625 km) that has data. Contains `generated_at`, `schema_version`, and per target, a list of cells: `name`, `lat`, `lng`, `stage` (or `not_enough_reports`), `report_count`, `latest_report_at`, `is_famous_spot`, and the top 3 evidence items (link, source, thumbnail URL from the original host, license/attribution, taken_at).
- `site/data/index.json`: the list of shards that exist, plus per shard which targets have `go_now` cells (lets the site point users to the nearest region with something in season).
- The site computes the user's geohash-2 and loads that shard plus its existing neighbours, then filters by distance (`DEFAULT_RADIUS_KM` 100, adjustable).
- Keep files small (no raw API responses, no images). Version the schema.

## Stretch goal: nearby outdoor events

**Only start this after milestone 4 is published and working.** If time runs short, skip it; the core must be complete first.

Goal: turn a `go_now` cell into a full outing by suggesting **outdoor, in-person** events near it on the same days (harvest festivals, autumn-leaf festivals, cherry blossom festivals, farmers' markets, guided hikes). Events are a companion to the target result, not a separate feed. For global scope, only attach events for **famous spots**, to keep API usage bounded.

- **Sources (official APIs only, free tiers):** Ticketmaster Discovery API (`TICKETMASTER_API_KEY`; coverage is mostly North America and Europe); SerpApi Google Events engine if available (check docs; counts against the same SerpApi budget and cache rules).
- **Model task (Gemma, strict JSON):** event title + description → `{ "is_outdoor": bool, "is_in_person": bool, "category": str, "fits_touch_grass": bool, "reason": str }`. Drop events that are indoor, online, or screen-based.
- **Matching:** up to 2 qualifying events within `EVENT_RADIUS_KM` (default 15) of the spot in the next 7 days, exported into the shard JSON.
- **UI:** a small "Make a day of it" section on the card with the event name, date, distance, and a link to the official listing. Never copy full event descriptions.

## Repository layout

```
peakseason/
  ingest/       fetchers (inaturalist.py, serpapi.py), runner, budget.py
  model/        model client, classification, extraction
  geo.py        geohash, cells, naming, haversine
  targets.py    load + validate target YAML
  aggregate.py  per-(cell, target) scoring (pure functions)
  export.py     write site/data/ (targets, index, shards)
  store.py      SQLite cache and usage tracking
  config.py     settings from env (pydantic-settings)
targets/        maple.yaml, sakura.yaml
prompts/        prompt text files
data/spots.yaml
site/           index.html, app.js, styles.css, data/ (generated JSON)
tests/
```

## Commands

```
uv sync                                              # install deps
ollama pull gemma3:4b                                # or the configured MODEL_NAME
uv run python -m peakseason.ingest                   # all targets, global
uv run python -m peakseason.ingest --target maple --bbox "-80,43,-79,44"   # dev: one target, small area
uv run python -m http.server -d site 8000            # preview the site locally
uv run pytest && uv run ruff check . && uv run ruff format --check .
```

Local runs are for development only (use `--bbox` to keep them small). In production, the ingest workflow regenerates and commits `site/data/`; Cloudflare Pages serves `site/`. Trigger a run manually with the "Run workflow" button (or `gh workflow run ingest.yml`).

## Environment variables

`MODEL_BASE_URL` (default `http://localhost:11434/v1`), `MODEL_NAME`, `SQLITE_PATH` (default `.cache/peakseason.db`, gitignored), `SERPAPI_API_KEY` (optional), `SERPAPI_CACHE_HOURS`, `SERPAPI_RESERVE`, `SERPAPI_MAX_CALLS_PER_RUN`, `MAX_PHOTOS_PER_RUN`, `CLASSIFY_DEADLINE_MIN`, `MAX_PHOTOS_PER_CELL`, `WINDOW_DAYS`, `INAT_USER_AGENT`, and for the stretch goal `TICKETMASTER_API_KEY`, `EVENT_RADIUS_KM`. Keep `.env.example` up to date.

See `docs/design.md` for the validated design and decision log (also: `site/data/run_stats.json` per run, `.github/workflows/ci.yml` for tests/lint, `in_season_signals` in shards).

## Coding conventions

- Small, typed functions; async for network I/O.
- Every external call has a timeout, retries with backoff, and a log line.
- Fetchers return normalized `Report` objects (with `source`, `target_id`, `lat`, `lng`, `cell`); nothing downstream depends on which source a report came from.
- All text handling is Unicode-safe; never assume English or ASCII in place names or posts.
- Tests use recorded fixtures (JSON files in `tests/fixtures/`), never live APIs. Mock the model client in tests. Include fixtures from at least three countries in different hemispheres/languages.
- The site must work with only the exported JSON; test it by opening it against fixture shards with no network calls (evidence thumbnails excepted).
- Prefer boring, readable code over clever code. Explain non-obvious decisions in a short comment.

## Milestones (Toronto time)

1. **Fri night:** scaffold, config, target loader (maple + sakura YAML with schema tests), geohash/cell helpers with tests, SQLite store, iNaturalist fetcher (global, paginated) with fixtures and tests.
2. **Sat morning:** Gemma photo classification with caching; annotation-based free reports; classification budget (per-cell cap, priority order); end-to-end maple ingest on a small bbox.
3. **Sat afternoon:** aggregation + sharded JSON export; site with location → shard loading, place cards, directions links, and plant-of-the-moment selector; SerpApi for famous spots with budget and cache.
4. **Sat evening:** ingest workflow on GitHub Actions (model cache, SQLite cache, commit, timeouts); Cloudflare Pages live; one successful global run via `workflow_dispatch`. Record CPU latency per photo and coverage numbers in NOTES.md. Stretch: events.
5. **Sun (before 2:59 AM):** README (with "What's next"), screenshots from several cities (e.g. Toronto, Tokyo, Seoul, Sydney) or a short video, DEV write-up. Ideally, visit a recommended park and include photos.

After each milestone, make sure tests pass and the site still works end to end before moving on.

### After the challenge (do not build now)

- Translated UI (ja, ko, zh-TW first).
- More targets from the "What's next" list.
- A health check: if `generated_at` is older than 5 days, the site shows a "data may be stale" notice.

## Write-up notes (for the DEV post)

Judges weight **writing quality** most heavily. As you build, keep `NOTES.md` updated with decisions, problems hit, and numbers (photos classified, model latency per photo, cells covered per run, SerpApi calls used vs. budget, agreement with iNaturalist annotations where available). The post must cover: what it does and how it gets people outside, demo link (Cloudflare Pages) or video, code, how it's built around open-source AI, and **why open innovation matters** (self-hosted multilingual inference on a free CI runner, no per-image cost, photos never sent to a closed API, swappable model, $0 to run and fully automatic, global with no vendor lock-in, and a new plant is just a new config and prompt). Lead with the global angle: the same open pipeline tells someone in Toronto when to see maples and someone in Kyoto or Taipei when to see sakura.

Partner categories to target: Best Use of Gemma, Best Use of SerpApi, Best Use of GitHub Copilot (via the GitHub Actions automation; mention any Copilot use too).
