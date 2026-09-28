# TechJobs Africa

Static-first tech job discovery for African candidates.

## Start here

Read `PROJECT_CONTEXT.md` completely before making architectural or implementation changes.

The first engineering phase is **M0 source discovery**. Do not implement production source adapters before M0 is complete.

## v0.1 architecture

- Astro static frontend
- Python ingestion
- JSON state on a private `data` Git branch
- GitHub Actions
- Cloudflare Pages Direct Upload
- MiniSearch/simple client filtering
- Telegram alerts
- Cloudflare Web Analytics
- No database
- No runtime backend

## First instruction for your VS Code coding agent

> Read `PROJECT_CONTEXT.md` completely and treat it as the authoritative v0.1 specification. Start with M0 source discovery. Do not implement speculative production adapters before discovery is recorded.


## Why `link-health.yml` is not included yet

The weekly link-health workflow is an M5 hardening task. It should only be added after
`ingest/link_health.py` exists and the persistent `data` branch workflow is implemented.
This prevents a scheduled workflow from failing before the application has reached that stage.
