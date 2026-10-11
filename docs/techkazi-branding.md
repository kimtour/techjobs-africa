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
