"""Global deduplication and canonical normalization tests."""

from canonical import (
    deduplicate_jobs,
    job_identity,
    normalize_url,
)


def test_normalize_url_strips_tracking_params():
    left = "https://in.indeed.com/viewjob?jk=abc123&utm_source=freehire.me"
    right = "https://in.indeed.com/viewjob?jk=abc123"

    assert normalize_url(left) == normalize_url(right)
    assert "utm_source" not in normalize_url(left)


def test_normalize_url_strips_www_and_trailing_slash():
    assert normalize_url("https://www.example.com/jobs/x/") == (
        normalize_url("https://example.com/jobs/x")
    )


def test_normalize_url_lowercases():
    assert normalize_url("HTTPS://Example.com/Jobs/ABC") == (
        "https://example.com/jobs/abc"
    )


def test_url_priority_over_ids_and_names():
    job = {
        "source": "indeed",
        "source_job_id": "zzz",
        "title": "Cloud Engineer",
        "company": "Acme",
        "location": "Chennai",
        "url": "https://in.indeed.com/viewjob?jk=xyz",
    }

    assert job_identity(job).startswith("url:")


def test_source_job_id_used_without_url():
    job = {
        "source": "greenhouse",
        "source_job_id": "42",
        "title": "SRE",
        "company": "Acme",
    }

    assert job_identity(job) == "id:greenhouse:42"


def test_company_title_location_fallback():
    job = {
        "source": "remoteok",
        "title": "DevOps Engineer",
        "company": "Acme",
        "location": "Remote",
    }

    assert job_identity(job).startswith("job:")


def test_company_title_location_normalization():
    left = {
        "company": "Acme Pvt Ltd",
        "title": "Cloud Engineer",
        "location": "Chennai, India",
    }

    right = {
        "company": "Acme Limited",
        "title": "cloud engineer",
        "location": "chennai india",
    }

    assert job_identity(left) == job_identity(right)


def test_dedupe_global_collapses_same_job_across_providers():

    url = "https://in.indeed.com/viewjob?jk=samejob"

    indeed = {
        "source": "indeed",
        "source_job_id": "s1",
        "title": "Cloud Engineer",
        "company": "Acme",
        "location": "Chennai",
        "url": url,
    }

    google = {
        "source": "google",
        "source_job_id": "g1",
        "title": "Cloud Engineer",
        "company": "Acme",
        "location": "Chennai",
        "url": url,
    }

    unique = deduplicate_jobs([indeed, google])

    assert len(unique) == 1
    assert unique[0]["source"] == "indeed"
    assert unique[0]["duplicate_sources"] == ["google"]


def test_dedupe_preserves_distinct_jobs():

    left = {
        "source": "himalayas",
        "source_job_id": "h1",
        "title": "DevOps Engineer",
        "company": "One",
        "location": "Remote",
        "url": "https://himalayas.app/jobs/one",
    }

    right = {
        "source": "remoteok",
        "source_job_id": "r2",
        "title": "QA Engineer",
        "company": "Two",
        "location": "Remote",
        "url": "https://remoteok.com/jobs/two",
    }

    unique = deduplicate_jobs([left, right])

    assert len(unique) == 2