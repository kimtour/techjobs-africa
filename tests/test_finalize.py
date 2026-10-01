import json

from ingest.finalize import finalize


def snapshots(tmp_path):
    old = tmp_path / "data"
    candidate = tmp_path / "candidate"
    for root, marker in ((old, "old"), (candidate, "new")):
        for directory in ("public", "canonical", "state"):
            (root / directory).mkdir(parents=True)
        (root / "public/jobs.json").write_text(marker)
        (root / "canonical/jobs.json").write_text(marker)
        (root / "state/occurrences.json").write_text(marker)
    (candidate / "state/health.json").write_text('{"status":"FAILED"}')
    (candidate / "state/last-run.json").write_text('{"run_id":"123","public_hash":"abc"}')
    return old, candidate


def test_failed_deployment_only_promotes_audit(tmp_path):
    old, candidate = snapshots(tmp_path)
    finalize(old, candidate, promote=False, deployment={"outcome": "not_published"})
    assert (old / "public/jobs.json").read_text() == "old"
    assert (old / "state/occurrences.json").read_text() == "old"
    assert json.loads((old / "state/health.json").read_text())["status"] == "FAILED"
    assert next((old / "state/publication-history").glob("*.jsonl")).exists()


def test_successful_deployment_promotes_candidate(tmp_path):
    old, candidate = snapshots(tmp_path)
    finalize(old, candidate, promote=True, deployment={"outcome": "success"})
    assert (old / "public/jobs.json").read_text() == "new"
    assert (old / "state/occurrences.json").read_text() == "new"
    assert json.loads((old / "state/last-known-good.json").read_text())["public_hash"] == "abc"
