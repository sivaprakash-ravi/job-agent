"""Enrichment priority and near-miss score tests (V1.1 Phase 5/12)."""

import collect_jobs
from job_matcher import (
    enrichment_priority,
    near_miss_score_from_details,
)


def raw_job(title, location="Chennai", description="", skills=None):
    return {
        "source": "workable",
        "source_job_id": f"job-{title.replace(' ', '-').lower()}",
        "title": title,
        "company": "Acme",
        "location": location,
        "description": description,
        "skills": skills or [],
    }


def test_priority_prefers_target_role():
    devops = raw_job("DevOps Engineer", description="AWS + Kubernetes")
    frontend = raw_job("Frontend Developer", description="React CSS")

    assert enrichment_priority(devops) > enrichment_priority(frontend)


def test_priority_orders_support_roles():
    support = raw_job(
        "Cloud Support Engineer",
        description="AWS, GCP, Linux, troubleshooting, monitoring",
        skills=["AWS", "GCP", "Linux", "Docker"],
    )

    marketing = raw_job("Brand Manager", description="social media")

    assert enrichment_priority(support) > enrichment_priority(marketing)
    assert 0 <= enrichment_priority(support) <= 100


def test_priority_never_zeros_target_jobs_with_thin_listings():
    thin = raw_job("Site Reliability Engineer")
    assert enrichment_priority(thin) >= 38


def test_stratified_orders_within_a_source_by_priority():
    job_a = raw_job("DevOps Engineer", description="AWS Kubernetes")
    job_b = raw_job("QA Engineer", description="test cases Jira")
    job_c = raw_job("Brand Manager", description="social media")

    ordered = [
        sorted(
            [job_c, job_a, job_b],
            key=enrichment_priority,
            reverse=True,
        )
    ][0]

    assert ordered[0]["title"] == "DevOps Engineer"
    assert ordered[-1]["title"] == "Brand Manager"


def test_stratified_still_spreads_across_sources():
    jobs = []

    for source in ("greenhouse", "himalayas", "remoteok", "freehire"):
        for index in range(12):
            jobs.append(
                {
                    "source": source,
                    "source_job_id": f"{source}-{index}",
                    "title": "DevOps Engineer",
                    "description": "AWS",
                    "location": "Remote",
                }
            )

    selected = collect_jobs._stratified_jobs(jobs, 10)

    assert len(selected) == 10
    assert len({job["source"] for job in selected}) == 4

    counts = {}

    for job in selected:
        counts[job["source"]] = counts.get(job["source"], 0) + 1

    assert max(counts.values()) - min(counts.values()) <= 1


def test_near_miss_score_ignores_experience_gate():
    details = {
        "score_breakdown": {
            "role_score": 35,
            "skill_score": 24,
            "location_score": 15,
            "experience_score": -30,
            "seniority_penalty": 0,
            "semantic_bonus": 0,
            "total": 44,
        }
    }

    near = near_miss_score_from_details(details)

    assert near == 84
    assert near > 44


def test_near_miss_applies_seniority_soft_penalty():
    details = {
        "score_breakdown": {
            "role_score": 35,
            "skill_score": 24,
            "location_score": 15,
            "seniority_penalty": 20,
        }
    }

    near = near_miss_score_from_details(details)

    assert near == 74