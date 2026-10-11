# TechKazi

Static-first tech job discovery for African candidates.

Live site: **https://techkazi.pages.dev/**. The chosen future custom domain is
**techkazi.com**; it is planned and not connected as part of this update.
See [branding and hosting](docs/techkazi-branding.md) for the migration and checks.

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

## Local frontend preview

The site reads `site/src/data/jobs.json`, a safe static export produced by the ingestion pipeline. It ships empty in the application branch; deployment automation will copy the private data-branch export into this path before building.

```bash
cd site
npm install
npm run dev
```

## Production deployment

This project uses Cloudflare Pages Direct Upload so the GitHub workflow can build from the private `data` branch and deploy only the resulting static files.

1. In Cloudflare, use the **Workers & Pages → Direct Upload** project named `techkazi`.
2. Create a Cloudflare API token with **Account → Cloudflare Pages → Edit** permission.
3. In GitHub repository Settings → Secrets and variables → Actions, add repository secrets `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID`.
4. Set the repository variable `CLOUDFLARE_PAGES_PROJECT` to `techkazi`.

The scheduled `Ingest and build static site` workflow deploys only when all three values are present. Tokens must never be committed or pasted into project files.

## First instruction for your VS Code coding agent

> Read `PROJECT_CONTEXT.md` completely and treat it as the authoritative v0.1 specification. Start with M0 source discovery. Do not implement speculative production adapters before discovery is recorded.


## Why `link-health.yml` is not included yet

The weekly link-health workflow is an M5 hardening task. It should only be added after
`ingest/link_health.py` exists and the persistent `data` branch workflow is implemented.
This prevents a scheduled workflow from failing before the application has reached that stage.
