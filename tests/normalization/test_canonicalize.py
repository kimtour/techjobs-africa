from ingest.models import RawJob
from ingest.normalize.canonicalize import canonicalize_ashby_job


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
