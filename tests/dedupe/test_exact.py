from ingest.dedupe.exact import canonicalize_apply_url, deduplicate_exact
from ingest.models import CanonicalJob, EligibilityLevel


def job(*, job_id: str, source: str, title: str, apply_url: str) -> CanonicalJob:
    return CanonicalJob(
        job_id=job_id,
        title=title,
        normalized_title=title.casefold(),
        eligibility_level=EligibilityLevel.UNKNOWN,
        eligibility_evidence="No location evidence",
        eligibility_source="title_location_rules",
        preferred_apply_url=apply_url,
        sources=[source],
    )


def test_known_tracking_parameters_are_removed_but_functional_parameters_remain():
    url = "https://employer.example/apply?id=7&utm_source=board&gclid=value&step=2"

    assert canonicalize_apply_url(url) == "https://employer.example/apply?id=7&step=2"


def test_same_application_url_from_two_sources_is_displayed_once():
    jobs = deduplicate_exact(
        [
            job(
                job_id="source-a:1",
                source="source-a",
                title="QA Engineer",
                apply_url="https://employer.example/apply?id=7&utm_source=source-a",
            ),
            job(
                job_id="source-b:2",
                source="source-b",
                title="QA Engineer",
                apply_url="https://employer.example/apply?id=7&utm_source=source-b",
            ),
        ]
    )

    assert len(jobs) == 1
    assert jobs[0].sources == ["source-a", "source-b"]


def test_similar_titles_with_distinct_application_urls_are_not_merged():
    jobs = deduplicate_exact(
        [
            job(
                job_id="source-a:1",
                source="source-a",
                title="Software Engineer",
                apply_url="https://employer.example/jobs/1",
            ),
            job(
                job_id="source-b:2",
                source="source-b",
                title="Senior Software Engineer",
                apply_url="https://employer.example/jobs/2",
            ),
        ]
    )

    assert len(jobs) == 2
