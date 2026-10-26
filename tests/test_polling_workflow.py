import json
from pathlib import Path

import yaml


def test_cloudflare_is_the_only_scheduler_and_workflows_do_not_overlap():
    # BaseLoader preserves the YAML key "on" (YAML 1.1 treats it as a boolean).
    workflow = yaml.load(
        Path(".github/workflows/ingest-and-build.yml").read_text(), Loader=yaml.BaseLoader
    )
    assert "schedule" not in workflow["on"]
    assert "workflow_dispatch" in workflow["on"]
    worker = json.loads(Path("scheduler/wrangler.jsonc").read_text())
    assert worker["triggers"]["crons"] == ["* * * * *"]
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
    assert "npx wrangler deploy --secrets-file /dev/stdin" in deployment


def test_private_state_is_separate_and_public_pr_checks_do_not_receive_secrets():
    checkout = yaml.load(
        Path(".github/actions/checkout-data/action.yml").read_text(), Loader=yaml.BaseLoader
    )
    assert checkout["inputs"]["repository"]["default"] == "kimtour/techkazi-data"
    assert checkout["runs"]["steps"][0]["with"]["ssh-key"] == "${{ inputs.ssh-key }}"
    assert checkout["runs"]["steps"][0]["with"]["ref"] == "data"
    for name in (
        "ingest-and-build",
        "deploy-site",
        "migrate-techkazi",
        "evaluate-jsearch",
        "employer-discovery",
    ):
        text = Path(f".github/workflows/{name}.yml").read_text()
        assert "./.github/actions/checkout-data" in text
        assert "git fetch origin data" not in text
        assert "DATA_REPO_SSH_KEY" in text
    ci = Path(".github/workflows/ci.yml").read_text()
    assert "pull_request:" in ci
    assert "secrets." not in ci
    assert "checkout-data" not in ci
    for path in Path(".github/workflows").glob("*.yml"):
        assert "pull_request_target" not in path.read_text()


def test_workflow_passes_selected_feed_sources_as_separate_arguments(tmp_path):
    import os
    import subprocess

    workflow = yaml.load(
        Path(".github/workflows/ingest-and-build.yml").read_text(), Loader=yaml.BaseLoader
    )
    step = next(x for x in workflow["jobs"]["ingest-and-build"]["steps"] if x.get("id") == "fetch")
    shim = tmp_path / "python"
    shim.write_text('#!/bin/sh\nprintf "%s\\n" "$@" > "$RECORDED_ARGS"\n')
    shim.chmod(0o755)
    recorded = tmp_path / "args.txt"
    env = {
        **os.environ,
        "PATH": str(tmp_path) + os.pathsep + os.environ["PATH"],
        "RECORDED_ARGS": str(recorded),
        "CANDIDATE_DIR": str(tmp_path / "candidate"),
        "REFRESH_JSEARCH": "true",
        "REFRESH_EMPLOYER": "false",
        "REFRESH_EMPLOYERS": "false",
    }
    for selected, expected in [
        (
            "myjobmag,corporate_staffing,ashby",
            ["--source", "myjobmag", "--source", "corporate_staffing", "--source", "ashby"],
        ),
        ("myjobmag", ["--source", "myjobmag"]),
        ("all", []),
        ("employers", ["--employers-only"]),
    ]:
        subprocess.run(
            ["bash", "-e", "-c", step["run"]], env={**env, "FETCH_SOURCE": selected}, check=True
        )
        args = recorded.read_text().splitlines()
        assert args == [
            "-u",
            "-m",
            "ingest.main",
            "--output-dir",
            str(tmp_path / "candidate"),
            *expected,
            "--refresh-jsearch",
        ]
