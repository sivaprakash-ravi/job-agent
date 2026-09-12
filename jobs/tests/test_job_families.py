"""V1.1.2 career-priority (P1 support / P2 QA / P3 dev) regression tests.

- profile.py remains the single source of truth for the priority order.
- Family detection inspects title + JD content; it NEVER loosens
  eligibility (a role still needs genuine profile alignment).
- Career priority steers ranking with a small boost only (never
  touching match_score), so relevance still wins overall.
"""

from collections import Counter

import collect_jobs
import job_matcher
import profile
import send_telegram
from job_matcher import (
    detect_job_family,
    job_rank_key,
    job_priority_tier,
    priority_profile,
    rank_jobs,
    rank_priority_boost,
    score_job,
)
from sources.base import (
    build_search_queries,
    query_family_for,
)


def raw(
    title,
    description="",
    location="Chennai, India",
    source="workable",
    seed="1",
):
    return {
        "source": source,
        "source_job_id": f"{source}-{seed}-{title.lower().replace(' ', '-')}",
        "title": title,
        "company": "Acme",
        "location": location,
        "url": (
            f"https://jobs.workable.com/view/{source}-{seed}/"
            f"{title.lower().replace(' ', '-')}"
        ),
        "description": description,
        "skills": [],
    }


SUPPORT_DESC = (
    "Troubleshoot and resolve production issues, incident "
    "management, root cause analysis, monitoring dashboards, "
    "SQL queries, service requests, deployment and rollback."
)

QA_DESC = (
    "Design and execute test cases, regression and functional "
    "testing, defect tracking in Jira, API testing with Postman."
)

DEVOPS_DESC = (
    "AWS, Kubernetes, Docker, CI/CD pipelines, Terraform, "
    "infrastructure as code, Linux, monitoring and deployment."
)


def assert_tier(title, expected_family, expected_tier, description):
    job = raw(title, description=description)

    assert detect_job_family(job) == expected_family

    meta = priority_profile(job)

    assert meta["priority_tier"] == expected_tier

    assert meta["career_priority"] == (
        profile.JOB_FAMILY_PRIORITY[expected_family]
    )


# ------------------------------------------------------------
# P1 - SUPPORT / OPERATIONS
# ------------------------------------------------------------

def test_application_support_engineer_is_p1():
    assert_tier(
        "Application Support Engineer",
        "application_support",
        "P1",
        SUPPORT_DESC,
    )


def test_technical_support_engineer_is_p1():
    assert_tier(
        "Technical Support Engineer",
        "technical_support",
        "P1",
        SUPPORT_DESC,
    )


def test_production_support_engineer_is_p1():
    assert_tier(
        "Production Support Engineer",
        "production_support",
        "P1",
        SUPPORT_DESC,
    )


def test_cloud_support_engineer_is_p1():
    assert_tier(
        "Cloud Support Engineer",
        "cloud_support",
        "P1",
        SUPPORT_DESC,
    )


# ------------------------------------------------------------
# P2 - QA
# ------------------------------------------------------------

def test_qa_engineer_is_p2():
    assert_tier(
        "QA Engineer",
        "qa_testing",
        "P2",
        QA_DESC,
    )


def test_software_test_engineer_is_p2():
    assert_tier(
        "Software Test Engineer",
        "qa_testing",
        "P2",
        QA_DESC,
    )


def test_automation_qa_is_p2():
    assert_tier(
        "QA Automation Engineer",
        "qa_testing",
        "P2",
        QA_DESC,
    )


# ------------------------------------------------------------
# P3 - DEVELOPMENT / DEVOPS / SRE / CLOUD
# ------------------------------------------------------------

def test_devops_engineer_is_p3():
    assert_tier(
        "DevOps Engineer",
        "devops",
        "P3",
        DEVOPS_DESC,
    )


def test_sre_is_p3():
    assert_tier(
        "Site Reliability Engineer",
        "sre",
        "P3",
        DEVOPS_DESC,
    )


def test_infrastructure_engineer_is_p3():
    assert_tier(
        "Infrastructure Engineer",
        "cloud_infrastructure",
        "P3",
        DEVOPS_DESC,
    )


# ------------------------------------------------------------
# DO NOT LOOSEN RELEVANCE
# ------------------------------------------------------------

def test_generic_customer_support_is_not_p1():
    job = raw(
        "Customer Support Representative",
        description=(
            "Answer inbound calls, resolve customer inquiries, "
            "call center, voice process, customer care."
        ),
    )

    assert detect_job_family(job) is None
    assert priority_profile(job)["priority_tier"] is None


def test_call_center_support_is_not_p1():
    job = raw(
        "Call Center Support",
        description="Handle customer inquiries over the phone.",
    )

    assert detect_job_family(job) is None


def test_generic_quality_roles_need_testing_evidence():
    job = raw(
        "Quality Engineer",
        description="Supplier quality audits, ISO procedures.",
    )

    assert detect_job_family(job) != "qa_testing"


# ------------------------------------------------------------
# RANKING: priority is a signal, NOT a relevance replacement
# ------------------------------------------------------------

def test_p1_low_relevance_never_outranks_p3_high_relevance():
    low_p1 = {
        "match_score": 20,
        "priority_tier": "P1",
        "priority_boost": 12,
        "rank_score": 32,
    }

    high_p3 = {
        "match_score": 95,
        "priority_tier": "P3",
        "priority_boost": 0,
        "rank_score": 95,
    }

    assert job_rank_key(low_p1) < job_rank_key(high_p3)


def test_p1_strong_support_ranks_above_slightly_stronger_p3():
    good_p1 = {
        "match_score": 85,
        "priority_tier": "P1",
        "priority_boost": 12,
        "rank_score": 97,
    }

    better_p3 = {
        "match_score": 95,
        "priority_tier": "P3",
        "priority_boost": 0,
        "rank_score": 95,
    }

    assert job_rank_key(good_p1) > job_rank_key(better_p3)


def test_rank_score_never_touches_match_score():
    job = raw(
        "Technical Support Engineer",
        description=SUPPORT_DESC,
    )

    result = score_job(job)

    assert result["priority_tier"] == "P1"
    assert result["rank_score"] == (
        result["match_score"]
        + profile.RANK_PRIORITY_BOOST["P1"]
    )


def test_rank_jobs_orders_by_blended_rank_key():
    devops = score_job(
        raw(
            "DevOps Engineer",
            description=DEVOPS_DESC,
        )
    )

    support = score_job(
        raw(
            "Technical Support Engineer",
            description=SUPPORT_DESC,
        )
    )

    assert devops["priority_tier"] == "P3"
    assert support["priority_tier"] == "P1"

    ranked = rank_jobs([devops, support])

    expected = sorted(
        ranked,
        key=job_rank_key,
        reverse=True,
    )

    assert [job["title"] for job in ranked] == [
        job["title"]
        for job in expected
    ]


# ------------------------------------------------------------
# ENRICHMENT SELECTION REPRESENTS ALL TIERS
# ------------------------------------------------------------

def test_enrichment_selection_keeps_all_priority_tiers():
    jobs = []

    for index in range(6):
        jobs.append(
            raw(
                "Application Support Engineer",
                description=SUPPORT_DESC,
                source="workable",
                seed=str(index),
            )
        )
        jobs.append(
            raw(
                "QA Engineer",
                description=QA_DESC,
                source="himalayas",
                seed=str(index),
            )
        )
        jobs.append(
            raw(
                "DevOps Engineer",
                description=DEVOPS_DESC,
                source="remoteok",
                seed=str(index),
            )
        )

    selected = collect_jobs._stratified_jobs(
        jobs,
        len(jobs),
    )

    tiers = {
        job_priority_tier(job)
        for job in selected
    }

    assert {"P1", "P2", "P3"} <= tiers


# ------------------------------------------------------------
# TELEGRAM PRIORITY LABEL
# ------------------------------------------------------------

def test_telegram_priority_label():
    job = {
        "priority_tier": "P1",
        "priority_label": "Application Support",
        "source": "workable",
        "title": "Application Support Engineer",
        "company": "Acme",
        "location": "Chennai",
        "url": "https://jobs.workable.com/view/1",
        "match_score": 85,
        "match_category": "Good match",
    }

    message = send_telegram.format_message([job])

    assert "🥇 P1 — Application Support" in message


# ------------------------------------------------------------
# profile.py REMAINS THE SINGLE SOURCE OF TRUTH
# ------------------------------------------------------------

def test_profile_is_single_source_of_truth():
    assert profile.JOB_FAMILY_PRIORITY["qa_testing"] == 2
    assert profile.PRIORITY_TIERS[2] == "P2"
    assert profile.RANK_PRIORITY_BOOST["P1"] == 12

    assert (
        job_matcher.JOB_FAMILY_PRIORITY
        is profile.JOB_FAMILY_PRIORITY
    )


def test_query_budget_is_balanced_across_priority_tiers():
    queries = build_search_queries(limit=9)

    tiers = Counter(
        profile.JOB_FAMILY_PRIORITY[
            query_family_for(query)
        ]
        for query in queries
        if query_family_for(query) != "generic"
    )

    assert tiers[1] >= 2
    assert tiers[2] >= 2
    assert tiers[3] >= 2


def test_query_family_tracking():
    assert query_family_for(
        "Application Support Engineer"
    ) == "application_support"

    assert query_family_for(
        "QA Engineer"
    ) == "qa_testing"

    assert query_family_for(
        "DevOps Engineer"
    ) == "devops"

    assert query_family_for(
        "Unrelated Query"
    ) == "generic"