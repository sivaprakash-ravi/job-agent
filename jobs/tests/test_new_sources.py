"""Tests for the new source adapters (Workable, Remotive, Jobicy, RSS)."""

from xml.etree import ElementTree

from sources import (
    jobicy_source,
    remotive_source,
    rss_source,
    workable_source,
)
from sources.base import build_search_queries, normalize_common


def make_element(tag, text):
    el = ElementTree.Element(tag)
    el.text = text
    return el


def test_workable_search_normalization_mocked(monkeypatch):
    fake_search = {
        "jobs": [
            {
                "id": "w1",
                "title": "Cloud Engineer - Remote",
                "state": "published",
                "company": {"name": "Acme"},
                "location": "Remote",
                "workplace": "Remote",
                "url": "https://jobs.workable.com/view/w1",
                "created": "2026-01-01T00:00:00Z",
                "description": "<p>Cloud infrastructure support experience preferred</p>",
                "requirementsSection": "<p>2+ years of experience</p>",
                "employmentType": "Full-time",
            }
        ]
    }

    def fake_fetch(url, max_bytes=None, timeout=None, headers=None):
        if "widget" in url:
            return {"name": "Acme Widget", "jobs": []}
        return fake_search

    monkeypatch.setattr(
        workable_source,
        "fetch_json",
        fake_fetch,
    )

    result = workable_source.run(["Cloud Engineer"])

    assert result["status"] == "ok"
    assert result["count"] == 1

    job = result["jobs"][0]

    assert job["source"] == "workable"
    assert job["company"] == "Acme"
    assert job["remote"] is True
    assert job["url"] == "https://jobs.workable.com/view/w1"
    assert "cloud infrastructure support" in job["description"].lower()
    assert job["employment_type"] == "full-time"
    assert job["search_query"] == "Cloud Engineer"
    assert job["normalized_identity"]


def test_workable_pagination_uses_next_page_token(monkeypatch):
    calls = []

    page1 = {
        "jobs": [
            {
                "id": "a",
                "title": "SRE",
                "state": "published",
                "url": "https://jobs.workable.com/view/a",
            }
        ],
        "nextPageToken": "token-2",
    }

    page2 = {
        "jobs": [
            {
                "id": "b",
                "title": "QA Engineer",
                "state": "published",
                "url": "https://jobs.workable.com/view/b",
            }
        ],
        "nextPageToken": "",
    }

    pages = [page1, page2]

    def fake_fetch(url, max_bytes=None, timeout=None, headers=None):
        if "widget" in url:
            return {"name": "Acme Widget", "jobs": []}

        calls.append(url)

        if "nextPageToken=token-2" in url:
            return pages[1]

        return pages[0]

    monkeypatch.setattr(
        workable_source,
        "fetch_json",
        fake_fetch,
    )

    result = workable_source.run(["SRE"])

    assert result["count"] == 2
    assert any("nextPageToken" in call for call in calls)


def test_remotive_normalization_mocked(monkeypatch):
    fake_payload = {
        "jobs": [
            {
                "id": "r1",
                "title": "DevOps Engineer",
                "company_name": "Acme",
                "url": "https://remotive.com/jobs/r1",
                "candidate_required_location": "Worldwide",
                "publication_date": "2026-01-01T00:00:00Z",
                "job_type": "full_time",
                "salary": "$60k - $80k",
                "tags": ["devops", "aws"],
                "description": "<p>2+ years of experience, Kubernetes, monitoring</p>",
            }
        ]
    }

    monkeypatch.setattr(
        remotive_source,
        "fetch_json",
        lambda *args, **kwargs: fake_payload,
    )

    result = remotive_source.run(["DevOps Engineer"])

    assert result["status"] == "ok"
    assert result["count"] == 1

    job = result["jobs"][0]

    assert job["source"] == "remotive"
    assert job["company"] == "Acme"
    assert job["remote"] is True
    assert job["salary"] == "$60k - $80k"
    assert job["employment_type"] == "full-time"
    assert job["skills"] == ["devops", "aws"]


def test_jobicy_normalization_mocked(monkeypatch):
    fake_payload = {
        "jobs": [
            {
                "id": "j1",
                "jobTitle": "Cloud Support Engineer",
                "companyName": "Acme",
                "jobGeo": "Remote",
                "jobType": ["Full-time"],
                "jobIndustry": "Technology",
                "jobLevel": "Entry level",
                "pubDate": "2026-01-01",
                "salaryCurrency": "USD",
                "salaryMin": 60,
                "salaryMax": 80,
                "salaryPeriod": "k/year",
                "jobDescription": "<p>Hands-on cloud support and infrastructure experience</p>",
            }
        ]
    }

    monkeypatch.setattr(
        jobicy_source,
        "fetch_json",
        lambda *args, **kwargs: fake_payload,
    )

    result = jobicy_source.run(["Cloud Support"])

    assert result["status"] == "ok"
    assert result["count"] == 1

    job = result["jobs"][0]

    assert job["source"] == "jobicy"
    assert job["title"] == "Cloud Support Engineer"
    assert job["remote"] is True
    assert "60 - 80" in job["salary"]


def test_rss_feed_normalization_mocked(monkeypatch):
    item = ElementTree.Element("item")
    title = ElementTree.SubElement(item, "title")
    title.text = "DevOps Engineer"
    link = ElementTree.SubElement(item, "link")
    link.text = "https://euroremote.eu/jobs/devops-1"
    description = ElementTree.SubElement(item, "description")
    description.text = "<p>Remote role, Kubernetes and CI/CD experience.</p>"
    pub_date = ElementTree.SubElement(item, "pubDate")
    pub_date.text = "Wed, 04 Feb 2026 10:00:00 +0000"

    monkeypatch.setattr(
        rss_source,
        "_fetch_feed",
        lambda url: ([item], None),
    )

    result = rss_source.run_euroremote(["DevOps"])

    assert result["status"] == "ok"
    assert result["count"] == 1

    job = result["jobs"][0]

    assert job["source"] == "euroremote"
    assert job["url"] == "https://euroremote.eu/jobs/devops-1"
    assert job["date_posted"] == "2026-02-04"


def test_normalize_common_canonical_schema_fields():
    job = normalize_common(
        source="greenhouse",
        title="Cloud Engineer",
        company="Acme",
        url="https://boards.greenhouse.io/acme/jobs/1",
        description="Hands-on GCP infrastructure",
    )

    assert job["apply_url"] == job["url"]
    assert job["posted_at"] == job["date_posted"]
    assert job["discovered_at"]
    assert job["content_hash"]
    assert job["normalized_identity"].startswith("url:")
    assert isinstance(job["requirements"], str)


def test_build_search_queries_expanded():
    queries = build_search_queries()
    lowered = [query.lower() for query in queries]

    assert len(queries) == len(set(queries))
    assert "DevOps Engineer" in queries
    assert "Site Reliability" in queries
    assert "cloud infrastructure engineer" in lowered
    assert "qa engineer" in lowered