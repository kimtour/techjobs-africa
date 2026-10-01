from datetime import UTC, datetime, timedelta

import pytest

from ingest.claim_slot import claim_slot

NOW = datetime(2026, 10, 1, 14, 1, tzinfo=UTC)
SLOT = "2026-10-01T14:00:00.000Z"


def test_claim_is_immutable_and_prevents_second_fetch(tmp_path):
    assert claim_slot(tmp_path, SLOT, "first", now=NOW)
    assert not claim_slot(tmp_path, SLOT, "second", now=NOW)
    assert '"run_id": "first"' in next((tmp_path / "state/scheduler-slots").iterdir()).read_text()


def test_manual_fetch_does_not_claim_a_slot(tmp_path):
    assert claim_slot(tmp_path, "", "manual", now=NOW)
    assert not (tmp_path / "state").exists()


@pytest.mark.parametrize(
    "slot",
    ["../unsafe", "2026-10-01T14:17:00.000Z", "2026-10-01T15:00:00.000Z", "not-a-date"],
)
def test_invalid_or_future_slot_cannot_fetch(tmp_path, slot):
    with pytest.raises(ValueError):
        claim_slot(tmp_path, slot, "test", now=NOW)
    assert not (tmp_path / "state").exists()


def test_stale_slot_is_not_replayed(tmp_path):
    with pytest.raises(ValueError):
        claim_slot(tmp_path, SLOT, "test", now=NOW + timedelta(hours=2))


def test_authenticated_scheduler_test_can_run_between_slots(tmp_path):
    assert claim_slot(tmp_path, "test-2026-10-01T14:01:00.000Z", "test", now=NOW)
