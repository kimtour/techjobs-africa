from pathlib import Path

from ingest.adapters.myjobmag import parse_myjobmag_feed

FIXTURE = Path("tests/fixtures/m0/myjobmag_detailed_feed.xml")


def test_detailed_feed_keeps_minimal_job_fields_only():
    jobs = parse_myjobmag_feed(FIXTURE.read_bytes())

    assert len(jobs) == 1
    job = jobs[0]
    assert job.external_id == "1346068"
    assert job.company == "CDL Human Resource"
    assert job.title.startswith("Domestic Assistant")
    assert str(job.apply_url) == "https://www.myjobmag.co.ke/a_fields.php?id=1346068"
