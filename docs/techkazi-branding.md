# TechKazi branding and hosting

Chosen on 11 October 2026: **TechKazi**, initially at
**https://techkazi.pages.dev/**, with **techkazi.com** as the future custom domain.

## Scope and acceptance

- Update the site heading, tab title, description, sharing metadata and favicon.
- Use the current Pages address for canonical URLs, robots and sitemap.
- Update current project documentation, package display names, crawler branding,
  the scheduler dashboard and the repository description/website link.
- Publish every accepted job at the exact requested address before switching
  `CLOUDFLARE_PAGES_PROJECT` to `techkazi` for future scheduled updates.
- Permanently redirect the old production address after verifying the new site.
- Verify the local/live feed controls and mobile layout, plus the existing
  scheduler state after its dashboard is redeployed.

The hosting migration is performed through **Migrate TechKazi hosting**. First
run `publish`; it creates or checks the exact Pages project, builds the accepted
data-branch export, deploys it, compares every live job ID to the build, and records
the verified publication. Then set `CLOUDFLARE_PAGES_PROJECT=techkazi` and run
`redirect-legacy`. Both stages serialize with ingestion and ordinary site deploys.
Secrets remain in GitHub Secrets. No source fetch or extra provider quota is needed.

## Identity and historical evidence

The repository remains `kimtour/techjobs-africa`. The existing Worker resource
`techjobs-africa-scheduler`, its Durable Object name and concurrency groups keep
their operational identities so the scheduler history, credentials and slot claims
continue intact. Their user-facing branding is TechKazi. Historical audit links,
old deployment URLs and recorded source-discovery evidence remain as originally
observed. Job IDs and the accepted job data do not change during a branding update.

## Future custom domain

`techkazi.com` is planned, not connected. Register it when ready, add it through
the TechKazi Pages project's Custom domains settings, then update the Astro `site`
value and deployed canonical/sharing metadata, robots and sitemap. Verify HTTPS
and redirects before treating the custom domain as the production address. No
domain purchase or dormant DNS route is made during the Pages migration.

## Rollback

Before the old address is redirected, leave the existing Pages project configured
if any new deployment check fails. After migration, restore a previous verified
TechKazi deployment or build the accepted data export through Deploy TechKazi site.
Never roll back job state merely to undo branding.

## Delivered and verified — 11 October 2026

- Brand/source commit: `f38df67`.
- [New Pages project and publication](https://github.com/kimtour/techjobs-africa/actions/runs/38164495033):
  successful. Exact address https://techkazi.pages.dev/, with all 1,398 accepted
  visible job IDs compared against the build. Canonical and sharing URLs, favicon,
  robots and sitemap verified on the live domain. The data branch records this
  frontend-only publication without changing accepted job identities or state.
- `CLOUDFLARE_PAGES_PROJECT` now equals `techkazi`. Repository description and
  homepage link display TechKazi and its current address.
- [Legacy address redirect](https://github.com/kimtour/techjobs-africa/actions/runs/38164615904):
  successful. The old production address returns permanent HTTP 301 redirects to
  the new address, including paths such as `/robots.txt`.
- [Scheduler dashboard deployment](https://github.com/kimtour/techjobs-africa/actions/runs/38164623449):
  successful. The live dashboard title is TechKazi; public status is healthy,
  retains 90 historical slots, and still reports the successful 21:00 EAT fetch.
  No extra provider fetch was requested by the migration.
- Validation: 193 Python tests, Python lint, six frontend behavior tests, Astro
  check/build and 17 scheduler behavior/runtime tests passed. The deployed
  scheduler workflow repeated its own runtime checks successfully.
- Local/live browser checks: scrolling, pagination 10 to 20 without moving other
  panels, empty Day recovery, Codekeeper search/category matching and mobile
  layout at 390px with no horizontal overflow. Feed bodies remain 416px desktop
  and 384px mobile. All 1,398 roles remain available on the new domain.

The future custom domain is **techkazi.com**. It is planned and not connected.
