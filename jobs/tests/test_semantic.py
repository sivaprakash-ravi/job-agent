"""Semantic relevance layer and provider health tests."""

from semantic_job import semantic_score
from source_runner import build_stats


def test_semantic_lexical_score_bounds():
    job = {
        "title": "Cloud Support Engineer",
        "description": (
            "AWS, Kubernetes, Linux, troubleshooting, monitoring, "
            "incident response, infrastructure, python scripts, "
            "CI CD pipelines and cloud operations."
        ),
    }

    score, notes = semantic_score(job)

    assert 0.0 <= score <= 1.0
    assert notes["backend"] == "lexical"


def test_semantic_relevant_beats_irrelevant():
    relevant = {
        "title": "DevOps Engineer",
        "description": (
            "AWS, GCP, Azure, Kubernetes, Docker, Terraform, Linux, "
            "CI/CD, monitoring, SRE, reliability, production support, "
            "Python, Java, incident management and troubleshooting."
        ),
    }

    irrelevant = {
        "title": "Brand Manager",
        "description": (
            "We need a marketing leader to grow our consumer brand "
            "through social media campaigns and influencer partnerships."
        ),
    }

    score_relevant, _ = semantic_score(relevant)
    score_irrelevant, _ = semantic_score(irrelevant)

    assert score_relevant > score_irrelevant


def test_semantic_empty_content_scores_zero():
    score, notes = semantic_score({"title": "", "description": ""})

    assert score == 0.0
    assert notes["note"] == "empty content"


def test_provider_health_recorded_in_stats():
    results = [
        {
            "provider": "greenhouse",
            "status": "ok",
            "count": 5,
            "error": "",
            "jobs": [
                {
                    "source": "greenhouse",
                    "title": "A",
                    "company": "X",
                }
            ],
            "latency_ms": 1234.5,
            "ran_at_utc": "2026-01-01T10:00:00+00:00",
        },
        {
            "provider": "lever",
            "status": "blocked",
            "count": 0,
            "error": "HTTP 404",
            "jobs": [],
            "latency_ms": 88.0,
            "ran_at_utc": "2026-01-01T10:00:00+00:00",
        },
    ]

    stats, _ = build_stats(results)

    assert "provider_health" in stats

    by_provider = {
        entry["provider"]: entry
        for entry in stats["provider_health"]
    }

    assert by_provider["greenhouse"]["latency_ms"] == 1234.5
    assert by_provider["lever"]["status"] == "blocked"
    assert by_provider["lever"]["count"] == 0