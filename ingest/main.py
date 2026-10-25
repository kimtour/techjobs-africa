"""Run approved-source ingestion and write deterministic static data files."""

from __future__ import annotations

import argparse
import json
import time
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from statistics import median
from tempfile import NamedTemporaryFile
from urllib.parse import unquote, urlparse

import yaml

from ingest.adapters.ashby import AshbyAdapter
from ingest.adapters.brightermonday import BrighterMondayAdapter
from ingest.adapters.corporate_staffing import CorporateStaffingAdapter
from ingest.adapters.elevolt import ElevoltAdapter
from ingest.adapters.employer_boards import AshbyEmployerAdapter, SocialDiscoveryAdapter
from ingest.adapters.expertini import ExpertiniSitemapAdapter
from ingest.adapters.fuzu import FuzuAdapter
from ingest.adapters.jsearch import GoogleJobsJSearchAdapter, queries_for_day
from ingest.adapters.myjobmag import MyJobMagAdapter
from ingest.adapters.openedcareer import OpenedCareerAdapter
from ingest.audit import public_hash, read_json, record_run, run_identity
from ingest.classify.tech import (
    classification_title,
    has_non_technical_exclusion,
    mixed_technology_roles,
)
from ingest.dedupe.exact import canonicalize_apply_url, deduplicate_exact
from ingest.expiry.absence import JobOccurrence, reconcile_occurrences
from ingest.export.static import build_public_files
from ingest.fetch import ObservedClient
from ingest.models import CanonicalJob, JobStatus, RawJob, SourceHealth, SourceHealthStatus
from ingest.normalize.canonicalize import canonicalize_raw_job, normalize_text
from ingest.registry_sources import active_factories, source_due

CONFIG_PATH = Path("config/sources.yaml")
AdapterFactory = Callable[[], object]
ADAPTERS: Mapping[str, AdapterFactory] = {
    "jsearch": GoogleJobsJSearchAdapter,
    "expertini": ExpertiniSitemapAdapter,
    "ashby": lambda: AshbyAdapter("talentsafari"),
    "brightermonday": BrighterMondayAdapter,
    "corporate_staffing": CorporateStaffingAdapter,
    "elevolt": ElevoltAdapter,
    "fuzu": FuzuAdapter,
    "myjobmag": MyJobMagAdapter,
    "openedcareer": OpenedCareerAdapter,
    "camunda": lambda: AshbyEmployerAdapter("camunda"),
    "blacksmith": lambda: AshbyEmployerAdapter("blacksmith"),
    "sdg": SocialDiscoveryAdapter,
}


def approved_source_ids(config_path: Path = CONFIG_PATH) -> list[str]:
    """Return enabled sources that have an implemented production method."""

    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    legacy = [
        source["id"]
        for source in config["sources"]
        if source.get("enabled") and source.get("production_method") and source["id"] in ADAPTERS
    ]
    _, registry_config = active_factories(config_path.parent)
    return legacy + list(registry_config)


def build_jobs(
    raw_jobs: Sequence[RawJob], *, rejections: list[dict] | None = None
) -> list[CanonicalJob]:
    """Retain roles with title evidence or narrowly verified technical context."""

    # Source category pages are discovery aids, not evidence that every listing is
    # a technology role. BrighterMonday's IT & Telecoms page, for example, can
    # contain HR and finance vacancies. Require evidence from the role itself;
    # ambiguous early-warning roles also need verified development context.
    technical_jobs = []

    def reject(raw: RawJob, reason: str) -> None:
        if rejections is not None:
            rejections.append(
                {"external_id": raw.external_id, "title": raw.title, "reason": reason}
            )

    for raw in raw_jobs:
        # The listing URL is also a source-provided label. Reject a record if it
        # names an excluded role, preventing malformed cards from pairing a
        # technical title with a non-technical application URL.
        url_label = unquote(urlparse(str(raw.source_url)).path).replace("-", " ").replace("/", " ")
        # Employer names in URL slugs are attribution, just as they are in titles.
        # Strip only an explicit matching suffix; retain the role's URL guard.
        normalized_url = normalize_text(url_label)
        company_suffix = normalize_text(raw.company or "")
        if company_suffix and normalized_url.endswith(" " + company_suffix):
            url_label = normalized_url[: -(len(company_suffix) + 1)]
        # A source advert can explicitly bundle IT Trainer with receptionist and
        # other vacancies. Permit it only when the same bundle is in the URL;
        # unrelated title/URL pairings still fail the malformed-card guard.
        mixed_listing = mixed_technology_roles(raw.title) and normalize_text(
            raw.title.rsplit(" at ", 1)[0]
        ) in normalize_text(url_label)
        if not mixed_listing and (
            has_non_technical_exclusion(classification_title(raw.title, raw.company))
            or has_non_technical_exclusion(url_label)
        ):
            reject(raw, "non_technical_function")
            continue
        job = canonicalize_raw_job(raw)
        if job.category:
            technical_jobs.append(job)
        else:
            reject(raw, "unclassified_title_or_unverified_context")
    return deduplicate_exact(technical_jobs)


def _write_json(path: Path, content: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as temporary:
        temporary.write(json.dumps(content, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
        temporary_path = Path(temporary.name)
    temporary_path.replace(path)


def run_ingestion(
    output_dir: Path,
    *,
    source_ids: Sequence[str] | None = None,
    adapters: Mapping[str, object] = ADAPTERS,
    refresh_jsearch: bool = False,
) -> dict[str, SourceHealth]:
    """Fetch each source independently and write safe static files on success."""

    started = datetime.now(UTC)
    run_id, workflow_url = run_identity()
    selected_ids = list(source_ids or approved_source_ids())
    source_config = {
        item["id"]: item for item in yaml.safe_load(CONFIG_PATH.read_text())["sources"]
    }
    registry_adapters, registry_config = active_factories(CONFIG_PATH.parent)
    adapters = {**adapters, **registry_adapters}
    source_config.update(registry_config)
    if any(sid.startswith("employer_") and sid not in registry_config for sid in selected_ids):
        raise ValueError("Employer sources require active status and full verification")
    gates = yaml.safe_load(Path("config/quality_gates.yaml").read_text())["quality_gates"]
    previous_jobs = [
        CanonicalJob.model_validate(job)
        for job in read_json(output_dir / "canonical/jobs.json", {"jobs": []})["jobs"]
    ]
    # Explicit source retirement is separate from absence/closure processing.
    # Preserve other providers' identities and remove retired attribution.
    previous_jobs = [
        job.model_copy(update={"sources": [source for source in job.sources if source != "bebee"]})
        for job in previous_jobs
        if not job.job_id.startswith("bebee:") and any(source != "bebee" for source in job.sources)
    ]
    previous_health = read_json(output_dir / "state/health.json", {"sources": {}})["sources"]
    previous_health.pop("bebee", None)
    baselines = read_json(output_dir / "state/source-baselines.json", {})
    baselines.pop("bebee", None)
    occurrences = [
        JobOccurrence.model_validate(item)
        for item in read_json(output_dir / "state/occurrences.json", {"occurrences": []})[
            "occurrences"
        ]
    ]
    occurrences = [item for item in occurrences if item.source_id != "bebee"]
    jobs_by_id = {job.job_id: job for job in previous_jobs}
    health: dict[str, SourceHealth] = {}
    rows: dict[str, dict] = {}
    warnings: list[str] = []

    def record_policy_skip(source_id, reason):
        old = previous_health.get(source_id, {})
        skipped = SourceHealth(
            source_id=source_id,
            status=SourceHealthStatus.SKIPPED,
            records_found=0,
            pages_fetched=0,
            crawl_complete=False,
            safe_to_process_absences=False,
            last_attempt_at=old.get("last_attempt_at"),
            last_success_at=old.get("last_success_at"),
            stop_reason=reason,
        )
        rows[source_id] = {
            "health": skipped.model_dump(mode="json"),
            "technical_jobs": 0,
            "new_jobs": 0,
            "updated_jobs": 0,
            "missing_jobs": 0,
            "retained_jobs": sum(source_id in j.sources for j in previous_jobs),
            "requests": [],
            "hours_since_success": None,
        }

    for source_id in selected_ids:
        if source_id in registry_config and not source_due(
            registry_config[source_id], previous_health.get(source_id, {}), started
        ):
            record_policy_skip(source_id, "employer_source_not_due")
            continue
        if pause_reason := source_config[source_id].get("fetch_paused_reason"):
            record_policy_skip(source_id, pause_reason)
            continue
        if source_id in ("linkedin", "jsearch"):
            kenya_now = started.astimezone(timezone(timedelta(hours=3)))
            if source_id == "jsearch" and source_ids is None and kenya_now.hour < 7:
                record_policy_skip(source_id, "before_morning_refresh_eat")
                continue
            old_attempt = previous_health.get(source_id, {}).get("last_attempt_at")
            # Refresh on the next Kenya calendar day, rather than drifting later
            # after a manual afternoon run. Keep the shared account within quota.
            if (
                not refresh_jsearch
                and old_attempt
                and datetime.fromisoformat(old_attempt)
                .astimezone(timezone(timedelta(hours=3)))
                .date()
                == started.astimezone(timezone(timedelta(hours=3))).date()
            ):
                record_policy_skip(source_id, "already_checked_today_eat")
                continue
            used = 0
            for path in (output_dir / "state/request-history").glob(f"{started:%Y-%m}-*.jsonl"):
                used += sum(
                    json.loads(line).get("source_id") in ("linkedin", "jsearch")
                    for line in path.read_text().splitlines()
                    if line.strip()
                )
            required_requests = 5 if source_id == "jsearch" else 2
            if used + required_requests > 160:
                record_policy_skip(source_id, "monthly_request_budget")
                continue
        factory = adapters.get(source_id)
        if factory is None:
            raise ValueError(f"No adapter is registered for {source_id!r}.")
        attempt_at = datetime.now(UTC)
        _write_json(
            output_dir / "state/fetch-progress.json",
            {
                "run_id": run_id,
                "source_id": source_id,
                "started_at": attempt_at.isoformat(),
                "status": "RUNNING",
            },
        )
        print(f"Fetch started: {source_id} at {attempt_at.isoformat()}", flush=True)
        tick = time.monotonic()
        old = previous_health.get(source_id, {})
        previous_for_source = {
            job.job_id: job
            for job in previous_jobs
            if source_id in job.sources and job.status == JobStatus.ACTIVE
        }
        observer = None
        fetched = []
        source_jobs = []
        rejected_jobs: list[dict] = []
        complete = False
        error_type = None
        status = SourceHealthStatus.FAILED
        reason = "fetch_failed"
        next_allowed = old.get("next_allowed_at")
        try:
            if next_allowed and datetime.fromisoformat(next_allowed) > attempt_at:
                status = SourceHealthStatus.BLOCKED
                reason = "retry_after_cooldown"
            else:
                next_allowed = None
                adapter = factory()
                policy = source_config[source_id]["crawl"]
                if hasattr(adapter, "max_pages"):
                    adapter.max_pages = policy["max_pages"]
                if hasattr(adapter, "queries") and policy.get("queries"):
                    adapter.queries = queries_for_day(
                        policy, started.astimezone(timezone(timedelta(hours=3))).date()
                    )
                if hasattr(adapter, "target_jobs"):
                    adapter.target_jobs = policy.get("target_jobs", adapter.target_jobs)
                if hasattr(adapter, "request_delay_seconds"):
                    adapter.request_delay_seconds = policy["request_delay_ms"] / 1000
                for attribute in ("_client", "_session"):
                    if hasattr(adapter, attribute):

                        def record_request(event):
                            path = (
                                output_dir / "state" / "request-history" / f"{started.date()}.jsonl"
                            )
                            path.parent.mkdir(parents=True, exist_ok=True)
                            with path.open("a", encoding="utf-8") as handle:
                                handle.write(
                                    json.dumps(
                                        {
                                            "run_id": run_id,
                                            "source_id": source_id,
                                            **event,
                                        },
                                        sort_keys=True,
                                    )
                                    + "\n"
                                )

                        observer = ObservedClient(
                            getattr(adapter, attribute),
                            policy,
                            on_event=record_request,
                        )
                        setattr(adapter, attribute, observer)
                        break
                fetched = adapter.fetch()
                if any(raw.source_id != source_id for raw in fetched):
                    raise ValueError("adapter returned a foreign source")
                source_jobs = build_jobs(fetched, rejections=rejected_jobs)
                if source_id in registry_config:
                    source_jobs = [
                        job.model_copy(update={"last_checked_at": attempt_at})
                        for job in source_jobs
                        if job.eligibility_level in {"CONFIRMED", "LIKELY"}
                    ]
                _write_json(
                    output_dir / "state/classification" / f"{source_id}.json",
                    {
                        "schema_version": 1,
                        "run_id": run_id,
                        "source_id": source_id,
                        "filtered_jobs": rejected_jobs,
                    },
                )
                complete = getattr(adapter, "crawl_complete", False)
                status = SourceHealthStatus.SUCCESS if complete else SourceHealthStatus.PARTIAL
                reason = None if complete else "pagination_incomplete"
                counts = baselines.get(source_id, [])
                reference = median(counts[-7:]) if counts else old.get("records_found", 0)
                raw_drop = reference and len(fetched) < reference * (
                    1 - gates["max_source_job_drop_percent"] / 100
                )
                tech_drop = previous_for_source and len(source_jobs) < len(previous_for_source) * (
                    1 - gates["max_source_job_drop_percent"] / 100
                )
                # JSearch returns a bounded, ranked sample, while accepted jobs
                # accumulate across queries/days. A smaller valid sample is not
                # evidence of an incomplete inventory. Absence expiry stays off.
                if source_id == "jsearch":
                    raw_drop = tech_drop = False
                verified_empty = (
                    source_config[source_id].get("allow_verified_empty", False)
                    and complete
                    and not fetched
                    and not reference
                )
                if (not fetched and not verified_empty) or raw_drop or tech_drop:
                    status = SourceHealthStatus.PARTIAL
                    reason = "suspicious_count_drop" if fetched else "unexpected_empty_result"
        except Exception as exc:  # Never log exception text: it may contain bodies or secrets.
            error_type = type(exc).__name__
            if error_type == "FetchBudgetExceeded":
                reason = "request_budget_exhausted"
            response = getattr(exc, "response", None)
            code = getattr(response, "status_code", None)
            if code in (401, 403, 429):
                status = SourceHealthStatus.BLOCKED
                reason = "rate_limited" if code == 429 else "access_blocked"
        finally:
            if observer is not None:
                next_allowed = observer.next_allowed_at
                closer = getattr(observer.client, "close", None)
                if closer:
                    closer()
        current = {job.job_id: job for job in source_jobs}
        # Observed records can refresh; missing records need separate absence evidence.
        if status == SourceHealthStatus.SUCCESS:
            if source_id == "jsearch":
                by_url = {
                    canonicalize_apply_url(str(job.preferred_apply_url)): key
                    for key, job in jobs_by_id.items()
                }
                for key, job in current.items():
                    url = canonicalize_apply_url(str(job.preferred_apply_url))
                    existing_id = key if key in jobs_by_id else by_url.get(url)
                    if existing_id is None:
                        jobs_by_id[key] = job
                        by_url[url] = key
                    elif existing_id == key:
                        jobs_by_id[key] = deduplicate_exact([job, jobs_by_id[key]])[0]
                    else:
                        # Preserve the accepted source's stable identity and fields.
                        jobs_by_id[existing_id] = deduplicate_exact([jobs_by_id[existing_id], job])[
                            0
                        ]
            else:
                for key, job in current.items():
                    existing = jobs_by_id.get(key)
                    jobs_by_id[key] = deduplicate_exact([job, existing])[0] if existing else job
            baselines[source_id] = [*baselines.get(source_id, []), len(fetched)][-10:]
        elif reason == "pagination_incomplete":
            for key, job in current.items():
                existing = jobs_by_id.get(key)
                jobs_by_id[key] = deduplicate_exact([job, existing])[0] if existing else job
        last_success = (
            datetime.now(UTC)
            if status == SourceHealthStatus.SUCCESS
            else old.get("last_success_at")
        )
        health[source_id] = SourceHealth(
            source_id=source_id,
            status=status,
            records_found=len(fetched),
            pages_fetched=observer.pages_fetched if observer else 0,
            crawl_complete=complete,
            safe_to_process_absences=(
                status == SourceHealthStatus.SUCCESS
                and complete
                and source_config[source_id].get("supports_absence_expiry", False)
                and any(item.source_id == source_id for item in occurrences)
            ),
            last_attempt_at=(
                old.get("last_attempt_at") if reason == "retry_after_cooldown" else attempt_at
            ),
            last_success_at=last_success,
            completed_at=datetime.now(UTC),
            duration_seconds=round(time.monotonic() - tick, 3),
            requests_made=observer.requests if observer else 0,
            retries=observer.retries if observer else 0,
            http_status_counts=dict(observer.status_codes) if observer else {},
            error_type=error_type,
            stop_reason=reason,
            next_allowed_at=next_allowed,
            consecutive_failures=(
                0
                if status == SourceHealthStatus.SUCCESS
                else old.get("consecutive_failures", 0) + 1
            ),
        )
        if status == SourceHealthStatus.SUCCESS or reason == "pagination_incomplete":
            # Seed pre-audit records on migration so the first run cannot close them.
            if not any(item.source_id == source_id for item in occurrences):
                occurrences = reconcile_occurrences(
                    occurrences,
                    list(previous_for_source.values()),
                    health[source_id],
                    observed_at=attempt_at,
                    closure_threshold=3,
                )
            occurrences = reconcile_occurrences(
                occurrences,
                source_jobs,
                health[source_id],
                observed_at=attempt_at,
                closure_threshold=3,
            )
            for occurrence in occurrences:
                if occurrence.source_id == source_id and not occurrence.active:
                    if occurrence.job_id in jobs_by_id:
                        jobs_by_id[occurrence.job_id] = jobs_by_id[occurrence.job_id].model_copy(
                            update={"status": JobStatus.EXPIRED}
                        )
        rows[source_id] = {
            "health": health[source_id].model_dump(mode="json"),
            "technical_jobs": len(source_jobs),
            "filtered_jobs": len(rejected_jobs),
            "filter_reasons": dict(Counter(item["reason"] for item in rejected_jobs)),
            "new_jobs": len(current.keys() - previous_for_source.keys()),
            "updated_jobs": sum(
                current[key] != previous_for_source[key]
                for key in current.keys() & previous_for_source.keys()
            ),
            "missing_jobs": len(previous_for_source.keys() - current.keys()),
            "retained_jobs": len(previous_for_source)
            if status != SourceHealthStatus.SUCCESS
            else 0,
            "requests": observer.events if observer else [],
            "hours_since_success": (
                round(
                    (datetime.now(UTC) - health[source_id].last_success_at).total_seconds() / 3600,
                    2,
                )
                if health[source_id].last_success_at
                else None
            ),
        }
        if status != SourceHealthStatus.SUCCESS:
            warnings.append(f"{source_id}: {status.value} ({reason}); previous listings retained.")
        # Persist each completed source so a later interruption leaves useful evidence.
        _write_json(
            output_dir / "state/health.json",
            {
                "schema_version": 1,
                "sources": {
                    **previous_health,
                    **{key: value.model_dump(mode="json") for key, value in health.items()},
                },
            },
        )
    jobs = list(jobs_by_id.values())
    # Preserve canonical occurrences; display exact cross-source duplicates once.
    active_jobs = deduplicate_exact(job for job in jobs if job.status == JobStatus.ACTIVE)
    previous_active = deduplicate_exact(
        job for job in previous_jobs if job.status == JobStatus.ACTIVE
    )
    publishable = any(item.status == SourceHealthStatus.SUCCESS for item in health.values())
    if previous_active and len(active_jobs) < len(previous_active) * (
        1 - gates["max_total_job_drop_percent"] / 100
    ):
        publishable = False
        warnings.append("Total listing drop exceeded quality gate; publication blocked.")
    if not publishable:
        jobs = previous_jobs
        active_jobs = previous_active
        warnings.append("No safe candidate to publish; last-known-good output retained.")
    public_files = build_public_files(active_jobs)
    previous_public = {
        filename: read_json(output_dir / "public" / filename, None) for filename in public_files
    }
    changed = public_hash(public_files) != public_hash(previous_public)
    if publishable:
        for filename, content in public_files.items():
            _write_json(output_dir / "public" / filename, content)
        _write_json(
            output_dir / "canonical/jobs.json",
            {
                "schema_version": 1,
                "jobs": [job.model_dump(mode="json") for job in jobs],
            },
        )
    if publishable:
        _write_json(
            output_dir / "state/occurrences.json",
            {
                "schema_version": 1,
                "occurrences": [item.model_dump(mode="json") for item in occurrences],
            },
        )
    _write_json(output_dir / "state/source-baselines.json", baselines)
    record_run(
        output_dir,
        {
            "schema_version": 1,
            "run_id": run_id,
            "workflow_url": workflow_url,
            "started_at": started.isoformat(),
            "completed_at": datetime.now(UTC).isoformat(),
            "outcome": "BLOCKED" if not publishable else "DEGRADED" if warnings else "SUCCESS",
            "publishable": publishable,
            "needs_attention": any(item.consecutive_failures >= 2 for item in health.values()),
            "public_changed": changed and publishable,
            "public_hash": public_hash(public_files),
            "sources": rows,
            "warnings": warnings,
        },
        _write_json,
    )
    _write_json(
        output_dir / "state/fetch-progress.json",
        {
            "run_id": run_id,
            "status": "COMPLETED",
            "completed_at": datetime.now(UTC).isoformat(),
        },
    )
    return health


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--source", action="append", dest="sources")
    parser.add_argument(
        "--refresh-jsearch",
        action="store_true",
        help="Refresh changed Google queries today; monthly quota still applies",
    )
    args = parser.parse_args()
    health = run_ingestion(
        args.output_dir, source_ids=args.sources, refresh_jsearch=args.refresh_jsearch
    )
    summary = ", ".join(f"{key}={value.status}" for key, value in health.items())
    print("Ingestion complete: " + summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
