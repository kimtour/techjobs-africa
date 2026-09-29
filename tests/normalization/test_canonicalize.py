from ingest.models import RawJob
from ingest.normalize.canonicalize import canonicalize_ashby_job, canonicalize_raw_job


def raw_ashby_job(title: str) -> RawJob:
    return RawJob(
        source_id="ashby",
        external_id="8a5c7ebf-02e3-4492-9efc-ce83b879757e",
        title=title,
        location="Nairobi, Kenya",
        source_url="https://jobs.ashbyhq.com/talentsafari/8a5c7ebf-02e3-4492-9efc-ce83b879757e",
        apply_url="https://jobs.ashbyhq.com/talentsafari/8a5c7ebf-02e3-4492-9efc-ce83b879757e/application",
    )


def test_ashby_external_id_is_the_stable_job_identity():
    original = canonicalize_ashby_job(raw_ashby_job("Software Engineer"))
    corrected = canonicalize_ashby_job(raw_ashby_job("Senior Software Engineer"))

    assert original.job_id == corrected.job_id
    assert original.normalized_title != corrected.normalized_title


def test_canonicalization_preserves_apply_url_and_eligibility():
    job = canonicalize_ashby_job(raw_ashby_job("Software Engineer"))

    assert str(job.preferred_apply_url).endswith("/application")
    assert job.eligibility_level == "CONFIRMED"
    assert job.is_agency_posting is True


def test_generic_source_uses_external_id_and_classifies_qa_title():
    raw = RawJob(
        source_id="elevolt",
        external_id="stable-listing-id",
        title="QA Automation Engineer",
        company="Example Technologies",
        location="Nairobi, Kenya",
        source_url="https://jobs.elevolt.co.ke/job/qa-automation-engineer",
        apply_url="https://jobs.elevolt.co.ke/job/qa-automation-engineer",
    )

    job = canonicalize_raw_job(raw)

    assert job.job_id == "elevolt:stable-listing-id"
    assert job.category == "QA / Testing"
    assert job.posting_company == "Example Technologies"
    assert job.hiring_company is None
    assert job.is_agency_posting is False
    assert job.city == "Nairobi"
    assert job.country_code == "KE"


def test_uses_explicit_title_city_when_source_location_is_missing():
    raw = RawJob(
        source_id="myjobmag",
        external_id="nyeri-role",
        title="Sales (Data Analysis & Insights)-Intern – Nyeri at Diageo",
        company="Diageo",
        source_url="https://example.com/nyeri-role",
        apply_url="https://example.com/nyeri-role",
    )

    job = canonicalize_raw_job(raw)

    assert (job.city, job.country, job.country_code) == ("Nyeri", "Kenya", "KE")
