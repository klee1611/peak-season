# Notes (decisions, problems, numbers for the write-up)

## Fri Oct 9, 2026 (evening, Toronto)

**Model choice.** Local Ollama 0.20 was too old to pull current models; upgraded to 0.40.2.
Chose `gemma4:e2b-it-qat` (Gemma 4, vision, 4.3 GB download) as the default `MODEL_NAME`.

**First end-to-end run** (`--target maple --bbox "-79.6,43.55,-79.2,43.85" --max-photos 12`, MacBook, local Ollama):
- 48 Acer observations in Toronto in 10 days, 42 with a displayable photo license, 21 cells, 0 with a phenology annotation.
- 12 photos classified, latency median 16.8 s, max 30.9 s (first call after load ~63 s).
- Results: 2 peak, 5 turning, 4 green, 1 rejected. Earlier probe: 4/6 rejected, and all four were
  correct rejections (two bark close-ups, one fallen leaf, one leaf in a hand). The prompt's
  "must show the tree's foliage" rule is doing its job.
- Exported 3 cells (cells only appear once they have a classified photo or an annotation signal).
- Worldwide, Acer had ~5,580 observations in the 10 days to Oct 9 (~28 API pages); only 99 had the
  "Colored Leaves" annotation, so Gemma does most of the work.

**Fixes found by running it:**
- `{"is_target_photo": false}` without a confidence failed validation and wasted a retry. Now valid.
- `--bbox "-80,43,-79,44"` was parsed by argparse as a flag. The CLI now accepts the documented form.
- Ingest fetched 10 days but aggregated 7, so photos 8–10 days old could spend model budget
  without ever reaching a card. Classification now only considers photos inside the window.

**Open / next:**
- GitHub runner CPU latency is the big unknown (laptop numbers above use Apple GPU via Metal).
- Cell names: generic "Toronto" for several cells; street names like "Glen Manor Dr" pass the
  address filter. Improve after famous spots exist (`data/spots.yaml` not written yet).

## Fri Oct 9, late evening: first run on GitHub Actions

Repo public at https://github.com/klee1611/peak-season. Test run via `workflow_dispatch`
(`target=maple`, Toronto bbox, `max_photos=10`), run 38016516934:
- Ollama install ~15 s; model pull on cache miss ~40 s (then cached); warm-up 4.6 s.
- **CPU latency on the free runner: median 59.3 s, max 76.3 s per photo** (vs 17 s on the
  laptop's Apple GPU). So 80 photos per run fit in the 90-minute classification deadline,
  about 160 photos a day worldwide at two runs per day.
- 48 observations fetched; 17 unclassified photos within the 7-day window; 10 classified;
  5 cells exported. Whole job 10 minutes. The bot commit worked (`data: ingest run ...`).

**Bug found before it bit:** a run limited to one target or a bbox rewrote the shards with only
its own results, which would have deleted every other target and region from the live site.
Filtered runs now keep cells outside their scope; a fresh result for the same cell wins.

## Prompt validation (maple)

Method: `python -m peakseason.validate --target maple`, 13 research-grade, CC-licensed
observations per annotation value, coarse-group agreement (Green Leaves ↔ green; Colored
Leaves ↔ turning/peak/past_peak). A rejected photo counts as a miss.

**Run 1, prompt v1: 16/26 = 62%, FAIL.** Colored Leaves 12/13, Green Leaves 4/13. Gemma called
green photos "turning": sunlit seedlings, a backlit green canopy, variegated leaves with cream
edges. Also found a flaw in the test: one observation can carry *both* Green and Colored Leaves
(a half-turned tree), and it was sampled into both groups.

**Fixes:** prompt v2 says sunlit/backlit, yellow-green, young and variegated leaves are green, and
"if unsure between green and turning, choose green". `validate.py` samples each observation once
and accepts a stage that fits any of its annotation values.

**Run 2, prompt v2: 21/26 = 81%, PASS.** 5 photos had both values (any stage agrees); without
them 16/21 = 76%. Caveat: v2 was written after looking at run-1 misses from overlapping photos,
so a held-out run on older photos (`--until 2025-11-30`) follows.

**Run 3, prompt v2, held out (`--until 2025-11-30`): 21/26 = 81%, PASS.** Photos observed
2006–2025 (UK, US, Finland and more); only one (406960446) overlaps run 2, because iNaturalist
sorts by upload date. No photo carried both values. Green Leaves 9/13, Colored Leaves 12/13,
0 rejected. Remaining misses: green leaves called turning/peak (4), coloured called green (1).

## Prompt validation (sakura)

**Run 1, prompt v1 (`--until 2026-05-31`): 24/26 = 92%, PASS.** Caveat, stated plainly: all 13
"Flower Buds" observations also carried "Flowers", so they accept any stage, and the test never
checked buds against bloom. What it does show: 12/13 blooming trees were judged as blooming
(first or full bloom), and 2/26 photos were wrongly rejected. A buds-only sample (early spring)
is the next check. First attempt crashed on a transient DNS error; `validate.py` now skips an
unfetchable photo instead of aborting.

**Decision (developer, 2026-10-10):** set `validated: true` for both maple and sakura.
