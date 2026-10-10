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
