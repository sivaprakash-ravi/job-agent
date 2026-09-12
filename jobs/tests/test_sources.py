"""Source adapter contract, failure isolation and stats tests."""

from concurrent.futures import ThreadPoolExecutor, as_completed

import source_runner
from sources.base import probe_result
from sources import greenhouse_source, himalayas_source, ashby_source, weworkremotely_source


def test_probe_result_contract():
    result = probe_result(
        "fake",
        "https://127.0.0.1:1/nothing",
        "unreachable",
    )

    assert set(result.keys()) == {
        "provider",
        "status",
        "count",
        "error",
        "jobs",
    }
    assert result["count"] == 0
    assert result["jobs"] == []
    assert result["status"] in {"blocked", "unavailable", "error"}


def test_source_failure_does_not_stop_others():
    def good(search_queries, locations):
        return {
            "provider": "good",
            "status": "ok",
            "count": 1,
            "error": "",
            "jobs": [
                {
                    "source": "good",
                    "source_job_id": "1",
                    "title": "Cloud Engineer",
                    "company": "Acme",
                }
            ],
        }

    def bad(search_queries, locations):
        raise RuntimeError("provider exploded")

    results = []

    with ThreadPoolExecutor(max_workers=2) as executor:
        future_map = {
            executor.submit(fn, [], []): name
            for name, fn in (("good", good), ("bad", bad))
        }

        for future in as_completed(future_map):
            name = future_map[future]

            try:
                results.append(future.result())
            except Exception as error:
                results.append(
                    {
                        "provider": name,
                        "status": "error",
                        "count": 0,
                        "error": str(error),
                        "jobs": [],
                    }
                )

    statuses = {result["provider"]: result["status"] for result in results}

    assert statuses["good"] == "ok"
    assert statuses["bad"] == "error"


def test_split_jobspy_result_expands_per_site():
    result = {
        "provider": "jobspy",
        "status": "ok",
        "count": 3,
        "error": "",
        "jobs": [
            {
                "source": "linkedin",
                "title": "DevOps",
                "company": "A",
            },
            {
                "source": "indeed",
                "title": "QA",
                "company": "B",
            },
            {
                "source": "linkedin",
                "title": "SRE",
                "company": "C",
            },
        ],
    }

    entries = source_runner.split_jobspy_result("JobSpy", result)

    by_provider = {entry["provider"]: entry for entry in entries}

    assert by_provider["LinkedIn"]["count"] == 2
    assert by_provider["Indeed"]["count"] == 1


def test_build_stats_aggregates():
    results = [
        {
            "provider": "one",
            "status": "ok",
            "count": 1,
            "error": "",
            "jobs": [{"source": "one", "title": "A", "company": "X"}],
        },
        {
            "provider": "two",
            "status": "blocked",
            "count": 0,
            "error": "HTTP 406",
            "jobs": [],
        },
    ]

    stats, all_jobs = source_runner.build_stats(results)

    assert stats["summary"]["total_discovered"] == 1
    assert len(stats["providers"]) == 2
    assert stats["providers"][1]["status"] == "blocked"


def test_greenhouse_normalization_mocked(monkeypatch):
    fake_payload = {
        "jobs": [
            {
                "id": 99,
                "title": "Cloud Engineer",
                "company_name": "Acme",
                "location": {"name": "Remote"},
                "content": "<p>Experience required: 2 years.</p>",
                "absolute_url": "https://boards.greenhouse.io/acme/jobs/99",
                "updated_at": "2026-01-01",
            }
        ]
    }

    monkeypatch.setattr(
        greenhouse_source,
        "fetch_json",
        lambda *args, **kwargs: fake_payload,
    )

    result = greenhouse_source.run(["Cloud Engineer", "DevOps"])

    assert result["status"] == "ok"
    assert result["count"] == 1

    job = result["jobs"][0]

    assert job["source"] == "greenhouse"
    assert job["title"] == "Cloud Engineer"
    assert job["remote"] is True
    assert job["url"].endswith("/jobs/99")


def test_ashby_normalization_mocked(monkeypatch):
    fake_payload = {
        "jobPostings": [
            {
                "id": "p1",
                "title": "QA Engineer",
                "isListed": True,
                "isRemote": True,
                "location": "Remote",
                "jobUrl": "https://jobs.ashbyhq.com/acme/p1",
                "descriptionPlain": "2+ years of experience",
                "publishedAt": "2026-01-01",
                "employmentType": "full-time",
            }
        ]
    }

    monkeypatch.setattr(
        ashby_source,
        "fetch_json",
        lambda *args, **kwargs: fake_payload,
    )

    result = ashby_source.run(["Cloud Engineer", "QA Engineer"])

    assert result["status"] == "ok"
    assert result["count"] == 1

    job = result["jobs"][0]

    assert job["source"] == "ashby"
    assert job["remote"] is True


def test_ashby_new_schema_mocked(monkeypatch):
    fake_payload = {
        "apiVersion": "1.0",
        "jobs": [
            {
                "id": "j1",
                "title": "SRE",
                "isListed": True,
                "isRemote": True,
                "location": "Remote",
                "jobUrl": "https://jobs.ashbyhq.com/acme/j1",
                "descriptionPlain": "2+ years of experience",
                "publishedAt": "2026-01-01",
                "employmentType": "FullTime",
                "team": "Engineering",
                "company": "Acme",
            }
        ],
    }

    monkeypatch.setattr(
        ashby_source,
        "fetch_json",
        lambda *args, **kwargs: fake_payload,
    )

    result = ashby_source.run(["Cloud Engineer", "SRE"])

    assert result["status"] == "ok"
    assert result["count"] == 1

    job = result["jobs"][0]

    assert job["source"] == "ashby"
    assert job["remote"] is True
    assert job["company"] == "Acme"


def test_weworkremotely_company_title_split():
    company, role = weworkremotely_source.split_company_title(
        "Tenchi Security: DevOps Engineer"
    )

    assert company == "Tenchi Security"
    assert role == "DevOps Engineer"


def test_weworkremotely_company_title_split_no_colon():
    company, role = weworkremotely_source.split_company_title(
        "Frontend Engineer"
    )

    assert company == ""
    assert role == "Frontend Engineer"


def test_himalayas_normalization_mocked(monkeypatch):
    fake_payload = [
        {
            "guid": "h1",
            "title": "DevOps Engineer",
            "companyName": "Acme",
            "locationRestrictions": ["Remote"],
            "description": "2 years of experience preferred",
            "applicationLink": "https://himalayas.app/jobs/h1",
            "pubDate": "2026-01-01",
            "employmentType": "full-time",
            "categories": ["devops"],
        }
    ]

    monkeypatch.setattr(
        himalayas_source,
        "fetch_json",
        lambda *args, **kwargs: fake_payload,
    )

    result = himalayas_source.run(["DevOps"])

    assert result["status"] == "ok"
    assert result["count"] == 1

    job = result["jobs"][0]

    assert job["source"] == "himalayas"
    assert job["remote"] is True