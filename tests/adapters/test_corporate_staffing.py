import json
from pathlib import Path

from ingest.adapters.corporate_staffing import (
    CorporateStaffingAdapter,
    parse_corporate_staffing_jobs,
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


def test_public_jobs_api_keeps_minimal_fields_only():
    payload = json.loads(Path("tests/fixtures/m0/corporate_staffing_job.json").read_text())
    jobs = parse_corporate_staffing_jobs(payload)

    assert len(jobs) == 1
    job = jobs[0]
    assert job.external_id == "450951"
    assert job.title == "ICT Interns Job Muranga County Government"
    assert job.company == "Muranga County Government"
    assert job.published_at is not None
    assert job.published_at.tzinfo is not None
    assert "description" not in job.model_dump()


def test_recovers_explicit_company_from_title_when_source_field_is_empty() -> None:
    jobs = parse_corporate_staffing_jobs(
        [
            {
                "id": 1,
                "date_gmt": "2026-09-28T14:26:00",
                "link": "https://example.com/job/1",
                "title": {"rendered": "Senior Frontend Engineer Job HFCB Group"},
            }
        ]
    )

    assert jobs[0].company == "HFCB Group"


def test_recovers_explicit_location_from_listing_content() -> None:
    jobs = parse_corporate_staffing_jobs(
        [
            {
                "id": 1,
                "link": "https://example.com/1",
                "title": {"rendered": "Developer"},
                "content": {"rendered": "<p>Job Location: Nairobi, Kenya.</p>"},
            }
        ]
    )

    assert jobs[0].location == "Nairobi, Kenya"


def test_fetch_follows_wordpress_page_count() -> None:
    first = [{"id": 1, "link": "https://example.com/1", "title": {"rendered": "First"}}]
    second = [{"id": 2, "link": "https://example.com/2", "title": {"rendered": "Second"}}]
    client = _PaginatedClient([_Response(first, "2"), _Response(second, "2")])

    jobs = CorporateStaffingAdapter(client=client, request_delay_seconds=0).fetch()

    assert [job.external_id for job in jobs] == ["1", "2"]
    assert [call[1]["page"] for call in client.calls] == [1, 2]
