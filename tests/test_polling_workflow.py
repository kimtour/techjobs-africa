from pathlib import Path

import yaml


def test_schedule_is_eat_day_weighted_and_workflows_do_not_overlap():
    # BaseLoader preserves the YAML key "on" (YAML 1.1 treats it as a boolean).
    workflow = yaml.load(
        Path(".github/workflows/ingest-and-build.yml").read_text(), Loader=yaml.BaseLoader
    )
    schedules = workflow["on"]["schedule"]
    hours = []
    for schedule in schedules:
        minute, hour, *_ = schedule["cron"].split()
        assert minute == "0"
        hours.extend((int(h) + 3) % 24 for h in hour.split(","))
    assert sorted(hours) == [1, 7, 9, 11, 13, 15, 17, 19, 21]
    assert workflow["concurrency"]["cancel-in-progress"] == "false"
    assert workflow["jobs"]["ingest-and-build"]["timeout-minutes"] == "25"


def test_source_budgets_are_bounded():
    from ingest.main import approved_source_ids

    config = yaml.safe_load(Path("config/sources.yaml").read_text())
    enabled = set(approved_source_ids())
    for source in config["sources"]:
        if source["id"] in enabled:
            policy = source["crawl"]
            assert policy["max_pages"] > 0
            assert policy["max_requests_per_run"] >= policy["max_pages"]
            assert len(policy["retry_delays_seconds"]) <= 2
            assert policy["request_delay_ms"] >= 500


def test_external_scheduler_cannot_bypass_slot_claim_or_expose_credentials():
    workflow = yaml.load(
        Path(".github/workflows/ingest-and-build.yml").read_text(), Loader=yaml.BaseLoader
    )
    assert "scheduler_slot" in workflow["on"]["workflow_dispatch"]["inputs"]
    steps = workflow["jobs"]["ingest-and-build"]["steps"]
    claim = next(index for index, step in enumerate(steps) if step.get("id") == "claim")
    fetch = next(index for index, step in enumerate(steps) if step.get("id") == "fetch")
    assert claim < fetch
    assert "steps.claim.outputs.proceed == 'true'" in steps[fetch]["if"]
    assert "SCHEDULER_GITHUB_TOKEN" not in Path("scheduler/wrangler.jsonc").read_text()
    deployment = Path(".github/workflows/deploy-scheduler.yml").read_text()
    assert "secrets.SCHEDULER_GITHUB_TOKEN" in deployment
    assert "--secrets-file', '/dev/stdin'" in deployment
