"""Funnel accounting, provider/query quality and overlap tests.

The funnel must classify every ranked job into exactly one terminal
stage so counts never double-count:
    enriched = verified + unverified = eligible + rejected
"""

from funnel import (
    provider_quality,
    query_quality,
    rejection_stage,
    source_overlap,
    stage_counter,
)


def ranked_job(
    title,
    category="Ignore",
    source="githubish",
    stage_reason="",
    location="Remote",
):
    details = {"filter_reasons": []}

    if category == "Ignore" and stage_reason:
        details["filter_reasons"] = [stage_reason]

    return {
        "title": title,
        "source": source,
        "location": location,
        "match_category": category,
        "match_details": details,
        "verification_status": "VERIFIED",
        "search_query": "DevOps",
    }


def test_rejection_stage_eligible():
    job = ranked_job("DevOps Engineer", category="Good match")
    assert rejection_stage(job) == "eligible"


def test_rejection_stage_location():
    job = ranked_job(
        "DevOps Engineer",
        stage_reason="Outside preferred locations",
    )
    assert rejection_stage(job) == "location_rejected"


def test_rejection_stage_experience_takes_priority():
    job = ranked_job(
        "DevOps Engineer",
        stage_reason=[
            "Outside preferred locations",
            "Mandatory experience exceeds 2 years (detected: 5 years)",
        ][-1],
    )
    assert rejection_stage(job) == "experience_rejected"

    multi = ranked_job(
        "DevOps Engineer",
        stage_reason=[
            "Mandatory experience exceeds 2 years (detected: 5 years)",
            "Outside preferred locations",
        ][-1],
    )
    assert rejection_stage(multi) == "location_rejected"


def test_rejection_stage_role():
    job = ranked_job(
        "Full Stack Developer",
        stage_reason="Insufficient role/skill relevance",
    )
    assert rejection_stage(job) == "role_rejected"


def test_rejection_stage_hard_fallback():
    job = ranked_job(
        "DevOps Engineer",
        stage_reason="Not full-time",
    )
    assert rejection_stage(job) == "hard_filter_rejected"


def test_stage_counter_no_double_counting():
    jobs = [
        ranked_job("A", category="Good match"),
        ranked_job("B", stage_reason="Outside preferred locations"),
        ranked_job("C", stage_reason="Mandatory experience exceeds 2"),
        ranked_job("D", stage_reason="Not full-time"),
    ]

    counts = stage_counter(jobs)

    assert counts["eligible"] == 1
    assert counts["location_rejected"] == 1
    assert counts["experience_rejected"] == 1
    assert counts["hard_filter_rejected"] == 1
    assert sum(counts.values()) == len(jobs)


def test_provider_quality_rows():
    results = [
        {
            "provider": "Workable",
            "jobs": [
                {"source": "workable", "title": "A"},
                {"source": "workable", "title": "B"},
            ],
        },
        {
            "provider": "Jobicy",
            "jobs": [{"source": "jobicy", "title": "C"}],
        },
    ]

    ranked = [
        ranked_job("A", source="workable", category="Good match"),
        ranked_job("B", source="workable"),
        ranked_job("C", source="jobicy", category="Possible match"),
    ]

    rows = provider_quality(results, ranked)

    by_source = {row["source"]: row for row in rows}

    assert by_source["workable"]["discovered"] == 2
    assert by_source["workable"]["enriched"] == 2
    assert by_source["workable"]["eligible"] == 1
    assert by_source["workable"]["relevance_rate_enriched"] == 0.5
    assert by_source["jobicy"]["eligible"] == 1


def test_query_quality_rows():
    ranked = [
        ranked_job("A", category="Good match", location="Remote"),
        ranked_job("B", category="Ignore"),
    ]

    rows = query_quality(ranked)

    devops = next(
        row
        for row in rows
        if row["search_query"] == "DevOps"
    )

    assert devops["enriched"] == 2
    assert devops["eligible"] == 1
    assert devops["relevance_rate"] == 0.5


def test_source_overlap_pairs():
    jobs = [
        {
            "title": "A",
            "source": "workable",
            "duplicate_sources": ["himalayas"],
        },
        {
            "title": "B",
            "source": "jobicy",
            "duplicate_sources": ["workable"],
        },
    ]

    rows = source_overlap(jobs)

    pairs = {
        (row["source_a"], row["source_b"]): row["overlap_count"]
        for row in rows
    }

    assert pairs[("himalayas", "workable")] == 1
    assert pairs[("jobicy", "workable")] == 1