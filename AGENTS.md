# AGENTS.md

This file provides guidance to coding agents when working with code in this repository.

## Project overview

TechJobs Africa — a minimalist, high-density tech job aggregator for African candidates. Static-first: no database, no runtime backend. The ingestion pipeline produces JSON that an Astro site serves statically.

## Quick commands

### Python ingestion
```bash
python -m ingest.main --output-dir ./output       # run ingestion
python -m pytest tests/                           # run tests
ruff check .                                      # lint
ruff format .                                     # format
```

### Frontend (Astro + plain CSS)
```bash
cd site
npm install
npm run dev       # local preview (reads site/src/data/jobs.json)
npm test          # frontend behavior regression tests
npm run check     # Astro/TypeScript validation
npm run build     # production build
npm run preview   # preview build output
```

### Run a single test
```bash
python -m pytest tests/test_main.py::test_function_name -v
```

## Architecture

### Ingestion pipeline (`ingest/`)

Pipeline stages (from `main.py`):
1. FETCH — adapters fetch from each source
2. EXTRACT → VALIDATE RAW → NORMALIZE — `normalize/canonicalize.py` converts `RawJob` to `CanonicalJob`
3. TECH-ONLY CLASSIFY — `classify/tech.py` filters to tech roles only
4. ELIGIBILITY CLASSIFY — `classify/eligibility.py` assigns CONFIRMED/LIKELY/VERIFY/RESTRICTED/UNKNOWN
5. DEDUPE — `dedupe/exact.py`
6. EXPIRY — `expiry/absence.py`
7. BUILD → VALIDATE → QUALITY GATES → output

Key modules:
- `ingest/models.py` — `RawJob`, `CanonicalJob`, `SourceHealth`, enums
- `ingest/adapters/` — source-specific adapters (ashby, myjobmag, corporate_staffing, openedcareer, elevolt)
- `ingest/normalize/` — `canonicalize.py`, `location.py`
- `ingest/classify/` — `eligibility.py`, `tech.py`
- `ingest/dedupe/` — `exact.py`
- `ingest/export/` — `static.py` builds `jobs.json`, `search-index.json`, `categories.json`, `countries.json`, `stats.json`

### Config (`config/`)

YAML-driven: `sources.yaml` (source definitions, methods, legal status), `geography.yaml` (African countries/cities), `categories.yaml` (tech taxonomy), `ats_boards.yaml`, `agencies.yaml`, `quality_gates.yaml`.

### Frontend (`site/`)

Astro static site. `site/src/lib/jobs.ts` exposes the `jobs` array (ACTIVE only) and display helpers. Reads `site/src/data/jobs.json` produced by the ingestion pipeline.

### Git state

- `main` — code only
- `data` branch — persistent JSON state (schema_version, canonical jobs, sources, health, deployment metadata)

## Key constraints

- Descriptions are never persisted (processed in-memory only)
- Job IDs use source + external_id, never mutable fields
- Fuzzy dedupe → review flag only, never auto-merge
- EMEA is never automatically Kenya-eligible
- 403/429/5xx never close a job; single 404 never expires
- Absence processing requires healthy + complete crawl + source supports it + not bootstrap
- No proxy/evasion logic for deliberate blocks
- Secrets only in GitHub Secrets: `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`

## Development phases

M0 discovery → M1 vertical slice (Ashby + Greenhouse) → M2 local sources → M3 processing → M4 frontend → M5 hardening → M6 launch.

Do not implement production source adapters before M0 discovery is complete. See `PROJECT_CONTEXT.md` for the full specification.

## Tests

Required test areas (from `PROJECT_CONTEXT.md` §22): eligibility rules, identity/dedupe, expiry/health, state/site validation. Fixtures live in `tests/fixtures/`.

## Source-panel delivery

See `docs/source-panels.md` for the interaction contract and browser acceptance checks.
Keep headers outside fixed-height scrolling feeds and preserve other sources’ positions
and state when loading more jobs or changing a source period. Verify locally and on
the deployed URL before declaring delivery complete.
