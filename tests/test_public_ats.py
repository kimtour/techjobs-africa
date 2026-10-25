from urllib.parse import parse_qs

import httpx
import pytest

from ingest.adapters.public_ats import PublicATSAdapter

EMPLOYERS = {"emp": {"id": "emp", "name": "Example", "sectors": []}}


def make(method, handler, pages=5):
    source = {
        "id": "test",
        "platform": method,
        "access_method": method,
        "employer_ids": ["emp"],
        "crawl": {"max_pages": pages},
        "collection": {
            "listing_url": "https://example.test/jobs",
            "site": "CX",
            "job_url_template": "https://example.test/careers/job/{id}",
            "public_board_url": "https://example.test/Careers",
        },
    }
    adapter = PublicATSAdapter(
        source,
        EMPLOYERS,
        httpx.Client(transport=httpx.MockTransport(handler)),
        validator=lambda url: None,
    )
    return adapter


def test_oracle_requires_all_declared_requisitions_and_keeps_stable_ids():
    offsets = []

    def respond(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nAllow: /")
        finder = parse_qs(request.url.query.decode())["finder"][0]
        offset = int(finder.rsplit("=", 1)[1])
        offsets.append(offset)
        records = [
            {
                "Id": str(offset + 1),
                "Title": "Software Engineer",
                "PrimaryLocation": "Nairobi",
                "PrimaryLocationCountry": "Kenya",
                "PostedDate": "2026-10-20",
                "PostingEndDate": "2026-11-20",
            }
        ]
        return httpx.Response(
            200, json={"items": [{"TotalJobsCount": 2, "requisitionList": records}]}
        )

    adapter = make("oracle", respond)
    jobs = adapter.fetch()
    assert adapter.crawl_complete and offsets == [0, 1]
    assert [job.external_id for job in jobs] == ["1", "2"]
    assert str(jobs[0].apply_url) == "https://example.test/careers/job/1"
    assert jobs[0].published_at.date().isoformat() == "2026-10-20"
    adapter = make("oracle", respond, pages=1)
    assert len(adapter.fetch()) == 1
    assert not adapter.crawl_complete


def test_workable_groups_same_posting_locations_and_excludes_talent_pools():
    jobs = [
        {
            "shortcode": "same",
            "title": "Software Engineer",
            "url": "https://example.test/job/same",
            "locations": [{"city": "Nairobi", "country": "Kenya"}],
            "published_on": "2026-10-20",
        },
        {
            "shortcode": "same",
            "title": "Software Engineer",
            "url": "https://example.test/job/same",
            "locations": [{"city": "London", "country": "United Kingdom"}],
        },
        {"shortcode": "pool", "title": "Talent Pool", "url": "https://example.test/job/pool"},
    ]

    def respond(request):
        return (
            httpx.Response(200, text="User-agent: *\nAllow: /")
            if request.url.path == "/robots.txt"
            else httpx.Response(200, json={"jobs": jobs})
        )

    adapter = make("workable", respond)
    found = adapter.fetch()
    assert adapter.crawl_complete and len(found) == 1
    assert found[0].external_id == "same"
    assert "Kenya" in found[0].location and "United Kingdom" in found[0].location
    assert "description" not in found[0].model_dump()


def test_workday_paginates_before_fetching_details_and_does_not_invent_posted_dates():
    paths = []

    def respond(request):
        paths.append(request.url.path)
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nAllow: /")
        if request.method == "POST":
            return httpx.Response(
                200,
                json={
                    "total": 1,
                    "jobPostings": [
                        {
                            "title": "Software Engineer",
                            "externalPath": "/job/Nairobi/New-Title_R123",
                            "locationsText": "Nairobi",
                            "postedOn": "Posted Today",
                        }
                    ],
                },
            )
        return httpx.Response(
            200,
            json={
                "jobPostingInfo": {
                    "jobReqId": "R123",
                    "title": "Software Engineer",
                    "location": "Nairobi",
                    "country": {"descriptor": "Kenya"},
                    "timeType": "Full Time",
                }
            },
        )

    adapter = make("workday", respond)
    found = adapter.fetch()
    assert adapter.crawl_complete and len(found) == 1
    assert found[0].external_id == "R123"
    assert found[0].published_at is None
    assert found[0].location == "Nairobi / Kenya"
    assert "/job/Nairobi/New-Title_R123" in paths


def test_workday_does_not_publish_a_truncated_search():
    def respond(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nAllow: /")
        return httpx.Response(
            200, json={"total": 2, "jobPostings": [{"externalPath": "/job/Nairobi/Engineer_R123"}]}
        )

    adapter = make("workday", respond, pages=1)
    assert adapter.fetch() == []
    assert not adapter.crawl_complete


def test_workable_rejects_a_missing_jobs_array():
    adapter = make(
        "workable",
        lambda request: (
            httpx.Response(200, text="User-agent: *\nAllow: /")
            if request.url.path == "/robots.txt"
            else httpx.Response(200, json={"error": "unavailable"})
        ),
    )
    with pytest.raises(ValueError):
        adapter.fetch()
    assert not adapter.crawl_complete


def test_workday_continuation_total_zero_is_not_a_new_empty_board():
    import json

    def respond(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nAllow: /")
        if request.method == "POST":
            offset = json.loads(request.content)["offset"]
            return httpx.Response(
                200,
                json={
                    "total": 2 if offset == 0 else 0,
                    "jobPostings": [{"externalPath": f"/job/Nairobi/Engineer_R{offset}"}],
                },
            )
        key = request.url.path.rsplit("_", 1)[1]
        return httpx.Response(
            200,
            json={
                "jobPostingInfo": {
                    "jobReqId": key,
                    "title": "Software Engineer",
                    "location": "Nairobi",
                    "country": {"descriptor": "Kenya"},
                    "additionalLocations": None,
                }
            },
        )

    collector = make("workday", respond)
    found = collector.fetch()
    assert collector.crawl_complete
    assert {job.external_id for job in found} == {"R0", "R1"}
