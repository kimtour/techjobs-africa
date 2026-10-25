# TechKazi

## Project overview

TechKazi helps people discover technology jobs in Kenya and remote roles that may be open to African applicants. It collects listings from configured public sources, filters and organizes them, and publishes a static site that links applicants to the original publisher.

### Purpose and users

The practical need is to reduce the effort of checking multiple job boards while making location and eligibility uncertainty visible. Intended users are job seekers browsing the site and the operator maintaining sources and data quality. A remote label alone is not treated as proof that a role accepts applicants from Kenya or elsewhere in Africa.

### Inputs and outputs

Inputs are approved job-source pages/APIs, employer listings, source configuration, geography/category rules and the previous ingestion state. Outputs are normalized job records, eligibility/category labels, a search index, source-health/fetch audits and the public static site. A private `data` branch retains state; the application branch holds code. Visitors follow original listing links to apply.

### Logic and workflow

Scheduled request → claim the fetch slot → fetch approved sources → normalize and classify → deduplicate → apply health-aware expiry/quality gates → export static JSON → build/deploy the site. Failed or blocked sources do not automatically close jobs. Descriptions are processed in memory rather than persisted, and uncertain fuzzy matches are flagged instead of automatically merged. Last-known-good output is retained where quality gates prevent safe publication.

### Integrations

Python ingestion feeds an Astro frontend with client-side filtering/search. A Cloudflare Worker coordinates GitHub Actions, which builds and uploads the site to Cloudflare Pages. Source adapters and configured APIs supply listings; optional Telegram alerts and Cloudflare Web Analytics support operation. The live address is https://techkazi.pages.dev/; `techkazi.com` remains a planned domain in the repository documentation.

### Running, maintenance and boundaries

The deployed fetch schedule is daily at **06:00, 09:00, 12:00, 15:00 and 19:00 Africa/Nairobi (EAT, UTC+3)**. Manual workflow runs remain available. Maintain adapters, access/request limits, classification rules, source health, scheduler credentials and fetch audits. Private-repository Actions minutes and any configured API usage consume account quotas; Cloudflare and other service costs depend on their accounts. Reducing fetch frequency controls resource use without implying a guaranteed zero monthly bill.

This is a job-discovery site, not an application-tracking system, job employer or guarantee of listing availability/eligibility. It has no user accounts, resume submission flow or runtime job database. Implemented behavior and source-specific limitations are documented in the repository; planned features are not presented as live.

## Start here

Employer onboarding: [registry, discovery and isolated trials](docs/employer-onboarding.md).
Execution and storage: [public code, private state and free fallbacks](docs/free-execution-and-private-state.md).
The private `kimtour/techkazi-data` repository retains the `data` branch and full
operational history; it is accessed only by trusted workflows using a dedicated
repository-scoped deploy key. Public PR checks do not receive this credential.

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
