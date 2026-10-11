# Cloudflare fetch scheduler

The dashboard is branded **TechKazi** and links to https://techkazi.pages.dev/.
The existing Worker and Durable Object identities are retained through the
branding migration so their scheduling history and credentials continue intact.
See [TechKazi branding and hosting](techkazi-branding.md).

Cloudflare requests the existing GitHub ingestion workflow at 01:00, 07:00,
09:00, 11:00, 13:00, 15:00, 17:00, 19:00, and 21:00 EAT every day. It runs a
one-minute Cron Trigger to reconcile due slots and check actual source-fetch
starts. This also catches a trigger that arrives late instead of depending on
one delivery at the exact scheduled minute. The site remains static; the Worker
only coordinates ingestion and exposes scheduler status.

## Deployment and credentials

The source is in `scheduler/`. Deploy using the **Deploy Cloudflare fetch
scheduler** workflow, with **test_fetch** enabled for initial setup. It installs
locked dependencies, runs behavior and local Cloudflare runtime tests, compiles
the Worker, checks Cloudflare access, deploys with an encrypted credential, and
requests an actual test fetch. Its run summary links the deployed status page.

Required GitHub repository Actions secrets:

- `CLOUDFLARE_ACCOUNT_ID`: existing account.
- `CLOUDFLARE_API_TOKEN`: must permit Account / Workers Scripts / Edit and
  Account / Account Settings / Read on this account. Retain Account / Cloudflare
  Pages / Edit for the existing site deployment. A Pages-only token cannot
  deploy a Worker. No zone or DNS permissions are needed.
- `SCHEDULER_GITHUB_TOKEN`: fine-grained GitHub personal access token restricted
  to `kimtour/techjobs-africa`, with Actions read/write and Contents read.
  Metadata read is automatic. No issues, administration, or other repositories
  are needed. Set an expiry and replace the secret before it expires; rerun the
  deployment workflow to provision the replacement.

Credentials are managed in GitHub Secrets. Deployment sends the scheduler token
through a pipe to Wrangler and provisions it as an encrypted Cloudflare Worker
secret. Never put tokens in source, data-branch records, workflow inputs, browser
URLs, or logs. The personal CLI authentication token is not reused for this
service.

The Cloudflare account needs an existing `workers.dev` subdomain. Deployment
checks this and reports missing permissions or subdomain configuration without
printing any secret values. This uses one SQLite Durable Object and a Worker;
no database is added to the site. Usage remains subject to Cloudflare account
limits. Deployment does not upgrade the account or change billing.

## Cutover

Cloudflare is active as the sole scheduler as of 1 October 2026. The native
GitHub cron has been removed; manual workflow dispatch remains available.
The [deployment](https://github.com/kimtour/techjobs-africa/actions/runs/36887559538)
and [end-to-end fetch](https://github.com/kimtour/techjobs-africa/actions/runs/36887615987)
succeeded, all seven approved sources reported SUCCESS, and the site was
published. The first regular 19:00 EAT fetch was dispatched at 19:00:12 and its
source-fetch step started at 19:00:44. The
[live status page](https://techjobs-africa-scheduler.kimani-mutua.workers.dev/)
tracks subsequent slots.

For a future replacement or rollback/redeployment:

Keep GitHub's existing native cron until the external scheduler has passed its
end-to-end test. Verify the test slot on the live status page, confirm the
**Ingest approved sources** step started, and inspect the completed workflow and
fetch audit. Then remove the native `schedule` block from
`.github/workflows/ingest-and-build.yml` and update the workflow regression test.
Do not leave both schedulers enabled: native scheduled runs do not have an
external slot ID and could fetch the sources a second time.

To roll back, remove the Worker's cron in Cloudflare or deploy a configuration
with an empty `triggers.crons` list, then restore GitHub's native schedule.
Manual ingestion via **Run workflow** remains available with an empty
`scheduler_slot`. Do not delete Durable Object history or slot claims to retry
an uncertain run; inspect its fetch audit first and use an unscheduled manual
run when a retry is warranted.

## Timing, retries, and duplicate protection

- A late tick catches up for 30 minutes. Startup does not replay older slots;
  a later outage records intervening missed slots without replaying stale jobs.
- GitHub's run history is checked before every dispatch. Requests are persisted
  before sending; an ambiguous timeout is reconciled before retrying.
- Dispatch retries wait three minutes and are capped at three attempts per slot.
  Once the matching run is visible, no further ingestion dispatch is sent.
- Before contacting sources, the workflow claims the slot in
  `data:state/scheduler-slots/` and pushes that immutable claim under the shared
  `techjobs-pipeline` concurrency lock. A failed claim push stops the workflow;
  another dispatch for the same slot skips fetching. Slots older than one hour
  are rejected. This is at-most-once source fetching per external slot, not a
  guarantee that every slot succeeds. A workflow that crashes after claiming a
  slot requires review and an unscheduled manual retry.
- The monitor reads the actual **Ingest approved sources** step start. A run
  that is merely accepted, queued, or doing setup does not count as fetching.

## Status and alerts

The deployed Worker provides:

- `/`: readable status page with EAT times, actual fetch starts, results,
  attempts, alerts, and links to GitHub runs; refreshes every 30 seconds.
- `/status`: public JSON ledger for the most recent 90 slots (about ten days).
- `/health`: the same payload with HTTP 503 when the latest slot has an error
  or alert, GitHub checks fail, or no scheduler tick has arrived for five minutes.
- `/test`: authenticated POST used by deployment to exercise a real fetch
  between normal slots. Requires the scheduler credential and creates a unique
  `test-` slot. Public POSTs and internal tick paths cannot trigger fetches.

Alerts are recorded durably, emitted to Cloudflare Worker logs, and dispatched
as deliberately failing **Fetch scheduler alert** GitHub workflows:

- `fetch_not_started`: no actual source fetch within ten minutes of the slot.
- `completion_overdue`: workflow has not completed within forty minutes.
- `workflow_failed`: fetch workflow failed or was cancelled, including existing
  ingestion source-health and quality-gate failures.

Each alert kind is sent once per slot. Failed alert dispatches retry every five
minutes. GitHub email/mobile delivery depends on the account's Actions
notification settings. Alerts are visible on the status page regardless of
subscription settings. No independent email/SMS sender is configured.

Cloudflare triggers and GitHub runners are still best-effort. Cloudflare can
request promptly while GitHub queues execution. A complete Cloudflare outage
cannot send its own immediate alert; `/health` is available for an independent
uptime monitor, and the ledger identifies missed slots after recovery. This
setup improves triggering and observability, but it does not promise exact
second start times or guaranteed notification delivery.

## Local checks

```sh
npm ci --prefix scheduler
npm test --prefix scheduler
npm run check --prefix scheduler
python -m pytest tests/
ruff check ingest tests
```

The runtime test opens a local-only port and exercises the compiled Worker,
SQLite Durable Object, public status page, and protected dispatch routes without
using live tokens or fetching any job source.
