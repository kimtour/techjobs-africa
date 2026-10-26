"""Compact, retryable employer candidates and honest daily collection coverage."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from ingest.audit import read_json
from ingest.registry_sources import collector_supported, load_sources, verification_gaps

EAT = ZoneInfo("Africa/Nairobi")


class EmployerLedger:
    def __init__(self, path: Path):
        self.path = path
        self.data = read_json(path, {"schema_version": 1, "sources": {}})

    def source(self, sid):
        return self.data["sources"].setdefault(sid, {"items": {}, "baseline_at": None})

    def observe(
        self,
        sid,
        raw,
        jobs,
        now,
        *,
        complete,
        publish_existing=False,
        known_before=None,
        validation_failed=(),
    ):
        state = self.source(sid)
        first_crawl = not state["baseline_at"]
        previous_ids = set(state["items"]) if known_before is None else known_before
        accepted = {job.job_id: job for job in jobs}
        ready = []
        for item in raw:
            if not item.external_id:
                continue
            key = str(item.external_id)
            job_id = f"{sid}:{key}"
            row = state["items"].setdefault(
                key,
                {
                    "external_id": key,
                    "job_id": job_id,
                    "first_seen_at": now.isoformat(),
                    "processing_status": "seen",
                },
            )
            row.update(
                title=item.title,
                detail_url=str(item.source_url),
                application_url=str(item.apply_url),
                last_seen_at=now.isoformat(),
            )
            if key in validation_failed:
                row.update(
                    processing_status="awaiting_validation",
                    retry_metadata={
                        **item.model_dump(mode="json"),
                        "technical_context": item.technical_context,
                        "applicant_africa": item.applicant_africa,
                    },
                )
                continue
            job = accepted.get(job_id)
            if job is None:
                row["processing_status"] = "filtered"
                continue
            is_baseline = row.get("baseline", False) or first_crawl
            row["baseline"] = is_baseline
            if is_baseline and not publish_existing:
                row["processing_status"] = "baseline"
                continue
            row["processing_status"] = (
                "published" if row.get("processing_status") == "published" else "validated"
            )
            row["last_validated_at"] = now.isoformat()
            ready.append(
                job.model_copy(
                    update={
                        "first_seen_at": datetime.fromisoformat(row["first_seen_at"]),
                        "last_checked_at": now,
                    }
                )
            )
        if complete:
            state["baseline_at"] = state["baseline_at"] or now.isoformat()
            state["last_complete_at"] = now.isoformat()
        state["new_ids"] = (
            len({str(item.external_id) for item in raw} - previous_ids) if not first_crawl else 0
        )
        state["new_eligible_ids"] = (
            sum(j.job_id.split(":", 1)[1] not in previous_ids for j in ready)
            if not first_crawl
            else 0
        )
        return ready

    def save(self, write_json):
        write_json(self.path, self.data)


def mark_published(data_dir: Path):
    path = data_dir / "state/employer-candidates.json"
    if not path.exists():
        return
    ledger = read_json(path, {})
    accepted = read_json(data_dir / "canonical/jobs.json", {"jobs": []})["jobs"]
    active = {job["job_id"] for job in accepted if job["status"] == "ACTIVE"}
    for source in ledger.get("sources", {}).values():
        for row in source["items"].values():
            if row.get("processing_status") == "validated" and row.get("job_id") in active:
                row["processing_status"] = "published"
    import json

    path.write_text(json.dumps(ledger, indent=2, sort_keys=True) + "\n")


def daily_coverage(data_dir: Path, now=None, config_dir=None):
    now = now or datetime.now(UTC)
    employers, sources = load_sources(config_dir) if config_dir else load_sources()
    today = now.astimezone(EAT).date().isoformat()
    health = read_json(data_dir / "state/health.json", {}).get("sources", {})
    ledger = read_json(data_dir / "state/employer-candidates.json", {"sources": {}})["sources"]
    metrics = read_json(data_dir / "state/employer-collection-metrics.json", {"sources": {}})[
        "sources"
    ]
    page_checks = read_json(data_dir / "state/employer-watch.json", {"sources": {}})["sources"]
    results = {}
    for sid, source in sources.items():
        h = health.get(sid, {})
        checked = h.get("last_attempt_at")
        checked_today = (
            checked and datetime.fromisoformat(checked).astimezone(EAT).date().isoformat() == today
        )
        configured = (
            source["status"] == "active"
            and not verification_gaps(source)
            and all(
                source["verification"].get(check) is True
                for check in ("trial_review", "publication_review")
            )
        )
        items = ledger.get(sid, {}).get("items", {}).values()
        pending = sum(
            row.get("processing_status")
            in {"seen", "awaiting_extraction", "awaiting_validation", "validated"}
            for row in items
        )
        if not configured:
            outcome = (
                "blocked"
                if source["status"] == "blocked"
                or page_checks.get(sid, {}).get("status") == "BLOCKED"
                else "manual"
                if source["status"] == "manual"
                else "awaiting_verification"
                if source["status"] in {"verified", "trial"} or collector_supported(source)
                else "unsupported"
            )
        elif not checked_today:
            outcome = "backoff" if h.get("consecutive_failures", 0) else "not_checked"
        elif h.get("status") == "SUCCESS" and h.get("crawl_complete"):
            outcome = "new_jobs" if metrics.get(sid, {}).get("new_jobs", 0) else "no_new_jobs"
        else:
            outcome = {"BLOCKED": "blocked", "PARTIAL": "partial"}.get(h.get("status"), "failed")
        results[sid] = {
            "outcome": outcome,
            "review_reason": source.get("review_reason"),
            "verification_gaps": verification_gaps(source),
            "configured": configured,
            "last_attempt_at": checked,
            "last_complete_at": h.get("last_success_at"),
            "pending_candidates": pending,
            "records_found": h.get("records_found", 0),
            "metrics": metrics.get(sid, {}),
        }
    companies = []
    for employer in employers.values():
        linked = []
        for sid in employer["source_ids"]:
            if sid not in results:
                continue
            row = results[sid]
            source = sources[sid]
            if employer["id"] not in source.get("verified_employer_ids", source["employer_ids"]):
                row = {**row, "configured": False, "outcome": "awaiting_employer_verification"}
            linked.append(row)
        outcomes = sorted({r["outcome"] for r in linked}) or ["unsupported"]
        companies.append(
            {
                "employer_id": employer["id"],
                "employer": employer["name"],
                "source_ids": employer["source_ids"],
                "page_monitoring": [
                    {
                        "source_id": sid,
                        "status": page_checks.get(sid, {}).get("status", "NOT_CHECKED"),
                        "checked_at": page_checks.get(sid, {}).get("checked_at"),
                        "method_suggestion": page_checks.get(sid, {}).get("method_suggestion"),
                    }
                    for sid in employer["source_ids"]
                ],
                "outcomes": outcomes,
                "daily_collection_configured": any(r["configured"] for r in linked),
                "checked_successfully_today": any(
                    r["outcome"] in {"new_jobs", "no_new_jobs"} for r in linked
                ),
            }
        )
    return {
        "schema_version": 1,
        "day_eat": today,
        "generated_at": now.isoformat(),
        "employers": len(companies),
        "recruitment_sources": len(results),
        "configured_employers": sum(e["daily_collection_configured"] for e in companies),
        "successfully_checked_employers": sum(e["checked_successfully_today"] for e in companies),
        "source_outcomes": dict(Counter(r["outcome"] for r in results.values())),
        "sources": results,
        "companies": companies,
    }
