# Free execution and private state

## Selected approach

User approved making `kimtour/techjobs-africa` public on 25 October 2026 after the
account exhausted its 2,000 private-repository hosted-runner minutes. Keep standard
GitHub-hosted Ubuntu runners for execution, and move accepted data plus operational
history to the private `kimtour/techkazi-data` repository, branch `data`.

GitHub's current documentation says standard hosted runners in public repositories
and self-hosted runners are free to use. Larger hosted runners remain chargeable;
artifact/cache limits still need monitoring. No paid budget, larger runner or
billing setting is enabled by this change.

Sources checked 25 October 2026:

- https://docs.github.com/en/billing/concepts/product-billing/github-actions
- https://docs.github.com/en/actions/concepts/runners/self-hosted-runners
- https://docs.gitlab.com/ci/pipelines/compute_minutes/
- https://developers.cloudflare.com/workers/platform/limits/

## Alternatives

1. Public code plus private state: primary solution, preserving existing Actions,
   static Astro publishing, Cloudflare scheduling, and one state-writing pipeline.
2. An existing always-on machine with a self-hosted runner: optional emergency
   capacity. GitHub currently documents free runner usage, but the owner bears
   electricity/network/security/maintenance costs. Never execute public fork PRs
   on a privileged persistent runner. No runner is installed by this change.
3. Local build and Cloudflare Direct Upload: available emergency frontend-only
   publication from accepted data. It consumes no Actions minutes. Verify data
   revision, absence of concurrent state writers and every deployed job ID. Do not
   improvise a second concurrent ingestion writer or delete scheduler slot claims.

GitLab Free supplies only 400 monthly compute minutes and would introduce another
credential set and writer coordination. It is not selected as automatic overflow.
Free Workers remain suitable for scheduling and status; moving the full Python
pipeline there would require a separate feasibility review and substantial changes.

## Data access and public-workflow boundary

`.github/actions/checkout-data` checks out only the private data repository into
`.private-data/`, using the dedicated `DATA_REPO_SSH_KEY` secret. The corresponding
write deploy key is restricted to that one repository. Personal CLI credentials
are used only by the human-authorized migration, never provisioned to a service.
`DATA_REPOSITORY` selects the private repository. The branch name stays `data`, so
immutable scheduler claims and history retain their identities.

All data writes still originate in the public code repository's serialized
`techjobs-pipeline` jobs. Never add an independent writer in the private repository;
GitHub concurrency groups do not coordinate across repositories. Actions are
disabled in the private state repository.

The scheduler retains its Worker/Durable Object identities and five daily EAT
slots. It reads public run/step evidence to choose the actual fetch owner when
duplicate dispatches occur; it no longer requires private state access. A run that
fails before ingestion, including a quota-blocked job, is not counted as fetching.

The PR validation workflow uses standard hosted runners, read-only permissions,
no deployment/data credentials and an empty sample job export. It never checks out
private data. There is no `pull_request_target` execution. Only read-only code
validation cancels superseded runs; production writers keep
`cancel-in-progress: false`.

Public workflow logs contain counts and sanitized error classes, not response
bodies, descriptions, credentials or recruiter contacts. Full operational audits
remain on the private data branch. Future public fetch artifacts contain only the
readable summary for seven days; deployable public-site artifacts last one day.

## Cutover and recovery

Before changing visibility:

1. Preserve the complete original `data` history in the private repository and
   compare its accepted canonical/public/state content.
2. Preserve historical workflow artifacts privately before removing their public
   copies; verify archive ZIPs and the private commit before cleanup.
3. Check all remaining code refs/history for tracked credentials and sensitive
   files. The included history scanner checks high-confidence credential patterns
   without printing matching values; it is not a proof against every possible
   secret format. Review research configuration and public build contents too.
4. Configure the scoped deploy key and update every data-reading/writing workflow.
5. Remove the original data branch only after the private copy is verified. A
   deleted ref does not guarantee GitHub purges unreachable objects immediately;
   confidential material must never be considered removed solely by branch
   deletion. Audit the preserved data history before proceeding and contact
   GitHub Support if sensitive blobs are found.
6. Publish only the audited code repository, then verify a standard-runner job,
   private-data checkout, real fetch, publication and scheduler status.

The private copy is the recovery source for operational history. Restore failed
code deployments through the existing Cloudflare project; do not rewrite job IDs,
data history, or immutable slot claims. Rotate the dedicated deploy key if needed
by replacing the repository key and GitHub secret together.
