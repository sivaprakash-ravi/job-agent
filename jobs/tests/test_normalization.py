"""Common job schema normalization tests."""

from sources.base import (
    build_locations,
    build_search_queries,
    normalize_common,
)


SCHEMA_KEYS = {
    "source",
    "source_job_id",
    "title",
    "company",
    "location",
    "remote",
    "url",
    "description",
    "date_posted",
    "employment_type",
    "experience",
    "salary",
    "skills",
    "search_query",
    "search_location",
    "raw_source_data",
}


def test_common_schema_contains_required_keys():
    job = normalize_common(
        source="greenhouse",
        title="Cloud Engineer",
        company="Acme",
    )

    assert set(job.keys()) >= SCHEMA_KEYS


def test_common_schema_defaults():
    job = normalize_common(
        source="greenhouse",
        title="Cloud Engineer",
        company="Acme",
    )

    assert job["source"] == "greenhouse"
    assert job["title"] == "Cloud Engineer"
    assert job["company"] == "Acme"
    assert job["remote"] is None
    assert job["skills"] == []
    assert job["date_posted"] == ""
    assert job["job_url"] == job["url"]


def test_remote_flag_preserved():
    job = normalize_common(
        source="remoteok",
        title="DevOps",
        company="Acme",
        remote=True,
    )

    assert job["remote"] is True


def test_source_job_id_falls_back_to_url():
    url = "https://example.com/jobs/1"

    job = normalize_common(
        source="test",
        title="SRE",
        company="Acme",
        url=url,
    )

    assert job["source_job_id"] == url


def test_raw_source_data_preserved():
    raw = {"requisition_id": "abc", "office": "Mumbai"}
    raw_job = {
        "title": "QA Engineer",
        "company": "Acme",
        "requisition_id": "abc",
        "office": "Mumbai",
    }

    job = normalize_common(
        source="test",
        title=raw_job["title"],
        company=raw_job["company"],
        raw=raw,
    )

    assert job["raw_source_data"] == raw


def test_locations_come_from_profile():
    locations = build_locations()

    assert locations
    assert "Chennai" in locations
    assert "Remote" in locations


def test_queries_are_broad_and_unique():
    queries = build_search_queries()

    assert len(queries) == len(set(queries))
    assert "DevOps Engineer" in queries
    assert "Site Reliability" in queries


def test_query_limit():
    queries = build_search_queries(limit=5)

    assert len(queries) == 5