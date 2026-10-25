"""Activation gates and daily due policy for registry-backed sources."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from functools import partial
from pathlib import Path

from ingest.adapters.registry_boards import SUPPORTED, RegistryBoardAdapter
from ingest.employer_registry import ROOT, STATES, read_registry

CHECKS = (
    "official_link",
    "collection_review",
    "local_access",
    "runner_access",
    "stable_ids",
    "application_links",
    "locations",
    "dates_reviewed",
    "complete",
)


def load_sources(config_dir: Path = ROOT / "config") -> tuple[dict, dict]:
    employers = {
        e["id"]: e for e in read_registry(config_dir / "employers.yaml", "employers")["employers"]
    }
    sources = {
        s["id"]: s
        for s in read_registry(config_dir / "employer-sources.yaml", "sources")["sources"]
    }
    for source in sources.values():
        if source["status"] not in STATES:
            raise ValueError("Unknown source lifecycle status")
        if not source["employer_ids"] or any(e not in employers for e in source["employer_ids"]):
            raise ValueError("Unresolved employer-source link")
        if source.get("refresh_hours", 0) < 24:
            raise ValueError("Employer boards must not run more than daily")
        if source.get("supports_absence_expiry"):
            raise ValueError("New employer sources require separate absence-policy verification")
    return employers, sources


def verification_gaps(source: dict) -> list[str]:
    evidence = source.get("verification", {})
    gaps = [name for name in CHECKS if evidence.get(name) is not True]
    if not evidence.get("evidence_paths"):
        gaps.append("evidence_paths")
    if not evidence.get("collection_basis"):
        gaps.append("collection_basis")
    if source["platform"] not in SUPPORTED or not source.get("board"):
        gaps.append("supported_board")
    return gaps


def active_factories(config_dir: Path = ROOT / "config") -> tuple[dict, dict]:
    employers, sources = load_sources(config_dir)
    factories, config = {}, {}
    boards = set()
    for sid, source in sources.items():
        if source["status"] != "active":
            continue
        if verification_gaps(source):
            raise ValueError(f"Active employer source lacks verification: {sid}")
        if not all(
            source["verification"].get(check) is True
            for check in ("trial_review", "publication_review")
        ):
            raise ValueError(f"Active employer source requires trial and publication review: {sid}")
        key = (source["platform"], source["board"], source.get("region"))
        if key in boards:
            raise ValueError("Shared recruitment board must have one active collection source")
        boards.add(key)
        factories[sid] = partial(RegistryBoardAdapter, source, employers)
        config[sid] = {
            **source,
            "enabled": True,
            "production_method": source["platform"],
            "allow_verified_empty": True,
        }
    return factories, config


def source_due(source: dict, health: dict, now: datetime) -> bool:
    last = health.get("last_attempt_at")
    if not last:
        return True
    last = datetime.fromisoformat(last).astimezone(UTC)
    failures = min(health.get("consecutive_failures", 0), 4)
    hours = min(source["refresh_hours"] * 2**failures, 168)
    cooldown = health.get("next_allowed_at")
    return now >= last + timedelta(hours=hours) and (
        not cooldown or now >= datetime.fromisoformat(cooldown).astimezone(UTC)
    )
