"""Job page enrichment tests (unverified handling)."""

from job_enricher import enrich_job


def test_unverified_when_fetch_fails(monkeypatch):

    def fake_fetch(job):
        return {
            "success": False,
            "status": "UNVERIFIED",
            "url": job.get("url", ""),
            "page_text": "",
            "json_ld": [],
            "json_ld_text": "",
            "error": "HTTP 403",
        }

    monkeypatch.setattr(
        "job_enricher.fetch_job_page",
        fake_fetch,
    )

    job = {
        "title": "Cloud Engineer",
        "company": "Acme",
        "url": "https://example.com/jobs/1",
    }

    result = enrich_job(job)

    assert result["detail_verification"]["success"] is False
    assert result["detail_verification"]["error"] == "HTTP 403"
    assert result["verification_status"] == "UNVERIFIED"


def test_verified_when_fetch_succeeds(monkeypatch):

    def fake_fetch(job):
        return {
            "success": True,
            "status": "VERIFIED_SOURCE",
            "url": job.get("url", ""),
            "page_text": "Full job description here.",
            "json_ld": [{"@type": "JobPosting"}],
            "json_ld_text": "JobPosting",
            "error": "",
        }

    monkeypatch.setattr(
        "job_enricher.fetch_job_page",
        fake_fetch,
    )

    job = {
        "title": "Cloud Engineer",
        "company": "Acme",
        "url": "https://example.com/jobs/1",
    }

    result = enrich_job(job)

    assert result["detail_verification"]["success"] is True
    assert result["verification_status"] == "VERIFIED"
    assert "full_job_page_text" in result
    assert "job_page_json_ld" in result
    assert "job_page_json_ld_text" in result


def test_enrichment_keeps_original_fields(monkeypatch):

    def fake_fetch(job):
        return {
            "success": False,
            "status": "UNVERIFIED",
            "url": job.get("url", ""),
            "page_text": "",
            "json_ld": [],
            "json_ld_text": "",
            "error": "timeout",
        }

    monkeypatch.setattr(
        "job_enricher.fetch_job_page",
        fake_fetch,
    )

    job = {
        "title": "QA Engineer",
        "company": "Acme",
        "url": "https://example.com/jobs/2",
        "salary": "7-9 LPA",
    }

    result = enrich_job(job)

    assert result["title"] == "QA Engineer"
    assert result["salary"] == "7-9 LPA"