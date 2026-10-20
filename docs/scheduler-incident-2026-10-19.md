# October 19 scheduler false-positive investigation

## Recorded evidence

All times below are UTC. GitHub run and job records were read on October 20,
along with the deployed Worker's read-only `/status` ledger.

| Event | Time |
| --- | --- |
| Scheduled slot | 2026-10-19 16:00:00 |
| Workflow 39282130307 created / run_started_at | 16:00:23 |
| ingest-and-build job started | 16:00:27 |
| Ingest approved sources step started | 16:01:02 |
| Ingest approved sources step completed | 16:10:05 |
| Watchdog detected and sent fetch_not_started, per ledger | 16:10:20.083 |
| Alert workflow 39283361056 created | 16:10:24 |
| ingest-and-build job completed successfully | 16:11:04 |
| Workflow record updated_at, also copied into ledger completed_at | 16:32:39 |

The final ledger contains both the sent alert and the correct source-fetch
start timestamp. It also shows successful subsequent slots, including October
20 at 04:00. The pipeline was operating during this incident.

Sources:

- https://github.com/kimtour/techjobs-africa/actions/runs/39282130307
- https://api.github.com/repos/kimtour/techjobs-africa/actions/runs/39282130307/jobs?per_page=100
- https://github.com/kimtour/techjobs-africa/actions/runs/39283361056
- https://techjobs-africa-scheduler.kimani-mutua.workers.dev/status

## Detection defect and evidence limits

The old policy tested only `!record.fetch_started_at` at the ten-minute
threshold. The engine populated that field only after observing the named
source-fetch step with a start timestamp. An executing workflow with absent
step details therefore produced `fetch_not_started`. The engine also proceeded
to alert classification after a jobs API exception, allowing an unavailable
observation to become a missing-start alert.

These are confirmed code paths. The original polling responses and Cloudflare
logs from 16:10:20 were not available in this investigation. Consequently,
delayed or incomplete step telemetry and a failed jobs request remain possible
triggers, rather than a proven historical API failure. A complete current jobs
response contains the timestamp and does not reproduce the old false alert.
The regression deliberately models absent step details at the recorded check
time and labels that reconstruction explicitly.

The fixture in `scheduler/test/fixtures/october-19.json` retains the relevant
recorded run, job, step, and alert timestamps. The test replays the running state
at 16:10:20.083 with step details absent, then supplies the recorded completed
response. The original policy dispatches a false start alert; the corrected
policy produces none and later records the actual source-fetch timestamp.

## Correction

Workflow execution and source-fetch telemetry are separate signals. Running or
completed workflow status satisfies the workflow-start check, including legacy
ledger records. The engine persists a valid workflow start timestamp only for
executing or completed runs; a queued run's `run_started_at` cannot establish
execution. Source-fetch timestamps still come exclusively from the actual,
non-skipped source-fetch step.

The existing `fetch_not_started` category now means the workflow is queued or
missing at ten minutes. Dashboard text, alert text, and scheduler documentation
state this explicitly. A workflow stuck in setup is covered by the existing
forty-minute completion deadline and runner timeout. An observation error stays
visible through `/health` and postpones incident classification until a
successful check. Previously sent alerts remain in the audit ledger.

## Validation and rollout

Local checks, with mocked GitHub responses and a local Cloudflare runtime:

```sh
npm ci --prefix scheduler
npm test --prefix scheduler
npm run check --prefix scheduler
```

Tests cover queued, pending, waiting, running, completed-success, failed,
cancelled, timed-out, and missing workflows, partial step telemetry, jobs API
failure and recovery, start evidence across eviction, completion deadlines,
legacy records, skipped duplicate steps, and existing duplicate protections.

After review and merge, deploy the scheduler through **Deploy Cloudflare fetch
scheduler** with `test_fetch=false`. Its default is true, so explicitly disable
that input. This deployment can be verified through GET `/status` and `/health`
and observation of the next regular scheduled slot. The **Verify deployed fetch
scheduler** workflow and POST `/test` launch real fetching and are unnecessary
for this correction. This investigation did not deploy or launch ingestion.
