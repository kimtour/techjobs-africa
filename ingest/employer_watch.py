"""Daily full-registry page monitoring; unresolved sources never publish vacancies."""

from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime, timedelta
from pathlib import Path

from ingest.audit import read_json
from ingest.dedupe.exact import canonicalize_apply_url
from ingest.employer_onboarding import write_json
from ingest.employer_probe import ProbeHTTP, probe_source
from ingest.employer_state import EAT, daily_coverage
from ingest.registry_sources import daily_slot, load_sources

MAX_SOURCES_PER_RUN = 150  # At most 1,800 discovery requests, separate from ingestion.


def review_change(row, previous):
    """Baseline silently; queue changed metadata without publishing or closing jobs."""
    baseline = previous.get("review_baseline")
    recognizable = (
        row.get("observed_vacancy_links")
        or row.get("pdf_urls")
        or row.get("technical_title_hints")
        or row.get("structured_job_count")
        or row.get("vacancy_state") == "EMPTY"
    )
    if row.get("status") not in {"DISCOVERED", "REACHABLE"} or not recognizable:
        if baseline is not None:
            row["review_baseline"] = baseline
        return None
    snapshot = {
        "source_url": row.get("input_url"),
        "urls": sorted(
            {
                canonicalize_apply_url(url)
                for url in row.get("observed_vacancy_links", []) + row.get("pdf_urls", [])
            }
        ),
        "technical_titles": sorted(set(row.get("technical_title_hints", []))),
    }
    row["review_baseline"] = snapshot
    if baseline is None or baseline.get("source_url") != snapshot["source_url"]:
        return None
    new_urls = sorted(set(snapshot["urls"]) - set(baseline.get("urls", [])))
    new_titles = sorted(
        set(snapshot["technical_titles"]) - set(baseline.get("technical_titles", []))
    )
    if not new_urls and not new_titles:
        return None
    return {
        "source_id": row["source_id"],
        "detected_at": row["checked_at"],
        "status": "pending_review",
        "new_urls": new_urls[:100],
        "technical_title_hints": new_titles[:20],
        "publication_approved": False,
        "reason": "changed_public_vacancy_metadata",
    }


def watch_due(source, previous, now):
    if source["status"] in {"active", "manual", "blocked", "retired"}:
        return False
    if previous.get("status") == "BLOCKED":
        return False  # A deliberate block requires review, not automatic daily retries.
    if now.astimezone(EAT).hour < daily_slot(source):
        return False
    checked = previous.get("checked_at")
    if not checked:
        return True
    checked = datetime.fromisoformat(checked)
    if previous.get("status") == "FAILED":
        return now >= checked + timedelta(days=min(2 ** min(previous.get("failures", 1), 3), 7))
    return now.astimezone(EAT).date() > checked.astimezone(EAT).date()


def run_watch(data_dir, *, now=None, workers=8, client=None):
    now = now or datetime.now(UTC)
    _, sources = load_sources()
    path = data_dir / "state/employer-watch.json"
    saved = read_json(path, {"schema_version": 1, "sources": {}})
    queue_path = data_dir / "state/employer-review-queue.json"
    queue = read_json(queue_path, {"schema_version": 1, "sources": {}})
    # Seed verified discovery evidence without rerunning previously blocked hosts.
    seed = read_json(Path("config/employer-discovery-seed.json"), {"sources": {}})
    for sid, evidence in seed["sources"].items():
        if sid in sources:
            saved["sources"].setdefault(sid, evidence)
    http = client or ProbeHTTP()
    attempted = 0
    try:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            due = sorted(
                (
                    source
                    for source in sources.values()
                    if watch_due(source, saved["sources"].get(source["id"], {}), now)
                ),
                key=lambda source: saved["sources"].get(source["id"], {}).get("checked_at", ""),
            )[:MAX_SOURCES_PER_RUN]
            pending = {pool.submit(probe_source, source, http): source["id"] for source in due}
            for future in as_completed(pending):
                sid = pending[future]
                old = saved["sources"].get(sid, {})
                row = future.result()
                signal = review_change(row, old)
                if signal:
                    pending_signal = queue["sources"].get(sid, {})
                    if pending_signal.get("status") == "pending_review":
                        signal["new_urls"] = sorted(
                            set(signal["new_urls"] + pending_signal.get("new_urls", []))
                        )[:100]
                        signal["technical_title_hints"] = sorted(
                            set(
                                signal["technical_title_hints"]
                                + pending_signal.get("technical_title_hints", [])
                            )
                        )[:20]
                    queue["sources"][sid] = signal
                row["failures"] = old.get("failures", 0) + 1 if row["status"] == "FAILED" else 0
                saved["sources"][sid] = row
                attempted += 1
                if attempted % 25 == 0:
                    write_json(path, saved)
                    print(f"Employer pages assessed: {attempted}", flush=True)
    finally:
        if client is None:
            http.close()
        saved.update(checked_at=now.isoformat(), requests_this_run=http.requests)
        write_json(path, saved)
        queue["checked_at"] = now.isoformat()
        write_json(queue_path, queue)
    coverage = daily_coverage(data_dir, now)
    pending_reviews = sum(
        row.get("status") == "pending_review" for row in queue["sources"].values()
    )
    write_json(data_dir / "state/employer-coverage.json", coverage)
    write_json(data_dir / f"state/employer-coverage/{coverage['day_eat']}.json", coverage)
    report = (
        f"# Employer collection — {coverage['day_eat']} EAT\n\n"
        f"Employers: {coverage['employers']}. Configured for daily vacancies: "
        f"{coverage['configured_employers']}. Successfully checked for vacancies today: "
        f"{coverage['successfully_checked_employers']}.\n\n"
        f"Discovery pages attempted this run: {attempted}; requests: {http.requests}. "
        "Page monitoring is not complete vacancy coverage.\n\n"
        f"Pending metadata review signals: {pending_reviews}. "
        "Signals are not approved vacancies and do not change collector counts.\n\n"
        "| Vacancy collection outcome | Sources |\n|---|---:|\n"
        + "".join(
            f"| {key} | {value} |\n" for key, value in sorted(coverage["source_outcomes"].items())
        )
    )
    (data_dir / "state/employer-coverage.md").write_text(report)
    return coverage


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    args = parser.parse_args()
    result = run_watch(args.data_dir)
    print(
        json.dumps(
            {
                key: result[key]
                for key in (
                    "employers",
                    "configured_employers",
                    "successfully_checked_employers",
                    "source_outcomes",
                )
            }
        )
    )


if __name__ == "__main__":
    main()
