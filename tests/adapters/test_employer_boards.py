import json
from pathlib import Path

import httpx
import pytest

from ingest.adapters.employer_boards import (
    SDG_URL,
    AshbyEmployerAdapter,
    SocialDiscoveryAdapter,
    parse_employer_ashby,
    parse_sdg_job,
)
from ingest.main import build_jobs, run_ingestion
from ingest.models import EligibilityLevel, SourceHealthStatus


def fixture(source):
    return json.loads(Path(f"tests/fixtures/m0/{source}_public_job.json").read_text())


def test_camunda_secondary_emea_location_stays_verify_with_original_identity():
    jobs = build_jobs(parse_employer_ashby(fixture("camunda"), "camunda"))
    assert len(jobs) == 1
    job = jobs[0]
    assert job.job_id == "camunda:b51b79c6-e2d8-428d-8cdc-0d1aae9792a9"
    assert job.posting_company == "Camunda"
    assert job.region == "EMEA" and job.country is None
    assert job.eligibility_level == EligibilityLevel.VERIFY
    assert job.workplace_type == "Remote"


def test_blacksmith_remote_secondary_south_africa_is_retained():
    payload = fixture("blacksmith")
    payload["jobs"][0]["descriptionPlain"] = "Synthetic confidential test sentinel"
    jobs = build_jobs(parse_employer_ashby(payload, "blacksmith"))
    assert len(jobs) == 1
    job = jobs[0]
    assert job.country == "South Africa" and job.workplace_type == "Remote"
    assert job.eligibility_level == EligibilityLevel.CONFIRMED
    assert "sentinel" not in job.model_dump_json()
    assert str(job.preferred_apply_url).endswith("/application")


@pytest.mark.parametrize("mutation", ["onsite", "foreign_url", "unlisted", "no_africa"])
def test_rejects_unsafe_or_non_african_remote_postings(mutation):
    payload = fixture("blacksmith")
    job = payload["jobs"][0]
    if mutation == "onsite":
        job.update(isRemote=False, workplaceType="OnSite")
    elif mutation == "foreign_url":
        job["applyUrl"] = "https://attacker.example/application"
    elif mutation == "unlisted":
        job["isListed"] = False
    else:
        job["secondaryLocations"] = [{"location": "Canada"}]
    assert parse_employer_ashby(payload, "blacksmith") == []


def sdg_body(*, location="worldwide", remote=True):
    return (
        '<script type="application/ld+json">'
        + json.dumps(
            {
                "@type": "JobPosting",
                "title": "Product Engineer (AI-Native)",
                "description": "Synthetic test description must not be persisted",
                "datePosted": "2026-10-06",
                "jobLocationType": "TELECOMMUTE" if remote else "ONSITE",
                "applicantLocationRequirements": {"@type": "Country", "name": location},
            }
        )
        + "</script>"
    )


def test_sdg_requires_own_remote_applicant_location_and_native_id():
    url = SDG_URL + "p/e5a41beaf52b01-product-engineer-ai-native"
    raw = parse_sdg_job(sdg_body(), url)
    assert raw.external_id == "e5a41beaf52b01"
    assert raw.published_date.isoformat() == "2026-10-06"
    job = build_jobs([raw])[0]
    assert job.region == "Worldwide" and job.eligibility_level == EligibilityLevel.CONFIRMED
    assert "description" not in raw.model_dump_json()
    assert parse_sdg_job(sdg_body(location="United States"), url) is None
    assert parse_sdg_job(sdg_body(remote=False), url) is None
    assert parse_sdg_job(sdg_body(), "https://foreign.example" + urlsplit_path(url)) is None


def urlsplit_path(url):
    return "/" + url.split("/", 3)[3]


def test_sdg_card_duplicates_make_one_detail_request_and_keep_application_url():
    url = SDG_URL + "p/e5a41beaf52b01-product-engineer-ai-native"
    card = (
        '<li class="position-details">'
        '<a href="/p/e5a41beaf52b01-product-engineer-ai-native">'
        "<h2>Product Engineer (AI-Native)</h2><ul><li>WorldWide</li></ul></a></li>"
    )
    requested = []

    def handler(request):
        requested.append(str(request.url))
        return httpx.Response(200, text=card * 3 if str(request.url) == SDG_URL else sdg_body())

    adapter = SocialDiscoveryAdapter(httpx.Client(transport=httpx.MockTransport(handler)))
    jobs = adapter.fetch()
    assert requested == [SDG_URL, url]
    assert len(jobs) == 1 and str(jobs[0].apply_url) == url
    assert adapter.crawl_complete


def test_blocked_employer_refresh_retains_accepted_jobs(tmp_path):
    adapter = AshbyEmployerAdapter(
        "camunda",
        httpx.Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(200, json=fixture("camunda"))
            )
        ),
    )
    run_ingestion(tmp_path, source_ids=["camunda"], adapters={"camunda": lambda: adapter})
    blocked = AshbyEmployerAdapter(
        "camunda", httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(403)))
    )
    health = run_ingestion(tmp_path, source_ids=["camunda"], adapters={"camunda": lambda: blocked})
    assert health["camunda"].status == SourceHealthStatus.BLOCKED
    assert not health["camunda"].safe_to_process_absences
    public = json.loads((tmp_path / "public/jobs.json").read_text())
    assert len(public["jobs"]) == 1
