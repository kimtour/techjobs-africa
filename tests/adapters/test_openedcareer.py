import json
from pathlib import Path

from ingest.adapters.openedcareer import (
    COMPUTER_SCIENCE_CATEGORY_ID,
    OpenedCareerAdapter,
    _company_from_title,
    parse_openedcareer_jobs,
)


class _Response:
    def __init__(self, payload, total_pages: str):
        self._payload = payload
        self.headers = {"X-WP-TotalPages": total_pages}

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class _PaginatedClient:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = []

    def get(self, url, *, params, timeout):
        self.calls.append((url, params, timeout))
        return next(self.responses)


def test_parses_minimum_openedcareer_listing_metadata() -> None:
    payload = json.loads(
        (Path(__file__).parents[1] / "fixtures/m0/openedcareer_job.json").read_text()
    )

    jobs = parse_openedcareer_jobs(payload)

    assert len(jobs) == 1
    assert jobs[0].source_id == "openedcareer"
    assert jobs[0].external_id == "53866"
    assert jobs[0].title == "Security Support Assistant – All Interested Applicants"
    assert str(jobs[0].source_url) == "https://openedcareer.com/job/security-support-assistant/"
    assert jobs[0].company is None
    assert "content" not in jobs[0].model_dump()


def test_extracts_explicit_company_from_listing_title() -> None:
    assert (
        _company_from_title("HoD Digital Business Support Systems at Safaricom PLC")
        == "Safaricom PLC"
    )
    assert _company_from_title("Security Support Assistant – All Interested Applicants") is None
    assert _company_from_title("Software Developer") is None


def test_fetch_uses_computer_science_taxonomy_and_follows_all_pages() -> None:
    first = [{"id": 1, "link": "https://example.com/1", "title": {"rendered": "First"}}]
    second = [{"id": 2, "link": "https://example.com/2", "title": {"rendered": "Second"}}]
    client = _PaginatedClient([_Response(first, "2"), _Response(second, "2")])

    jobs = OpenedCareerAdapter(client=client, request_delay_seconds=0).fetch()

    assert [job.external_id for job in jobs] == ["1", "2"]
    assert all(
        call[1]["job_listing_category"] == COMPUTER_SCIENCE_CATEGORY_ID for call in client.calls
    )
