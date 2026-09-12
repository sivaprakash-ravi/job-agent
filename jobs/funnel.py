"""Relevance-funnel accounting.

Tracks every job that leaves the pipeline and why, with no double
counting. Stages follow the pipeline:

    discovered -> normalized (unique) -> enrichable/duplicate
               -> enrichment_skipped | enriched
               -> verified | unverified
               -> qualified | possible_match | rejected
                  (one terminal rejection_stage per rejected job)

A job is counted exactly once at each boundary:
    unique    = enrichment_skipped + enriched
    enriched  = verified + unverified
              = qualified + possible_matches + rejected

Also produces provider quality, query quality and cross-source
overlap metrics used to steer the next run.
"""

import re
from collections import Counter, defaultdict

from canonical import job_identity
from job_matcher import (
    POSSIBLE_MATCH,
    QUALIFIED,
    job_qualification,
)
from sources.base import query_family_for


# ============================================================
# REJECTION STAGE CLASSIFICATION
# ============================================================

REJECTION_STAGES = frozenset(
    [
        "experience_rejected",
        "location_rejected",
        "role_rejected",
        "hard_filter_rejected",
    ]
)

def rejection_stage(job):
    """Return the single terminal stage for a ranked job.

    Non-rejected jobs return their explicit qualification state
    ("qualified" or "possible_match"). Every rejected job maps to one
    rejection stage by priority: experience > location > role > other.
    """
    category = job.get("match_category")

    if category != "Ignore":
        return job_qualification(job)

    details = job.get("match_details") or {}
    reasons = details.get("filter_reasons") or []

    if not reasons:
        return "hard_filter_rejected"

    for reason in reasons:
        if reason.startswith(
            "Mandatory experience exceeds"
        ):
            return "experience_rejected"

    for reason in reasons:
        if reason == "Outside preferred locations":
            return "location_rejected"

    for reason in reasons:
        if reason == "Insufficient role/skill relevance":
            return "role_rejected"

    return "hard_filter_rejected"


def stage_counter(jobs):
    """Count terminal rejection stages across ranked jobs."""
    return Counter(
        rejection_stage(job)
        for job in jobs
    )


# ============================================================
# PROVIDER QUALITY
# ============================================================

def provider_quality(provider_results, ranked):
    """Per-provider discovered/enriched/verified/eligible + rate.

    discovered counts use the job records actually produced by each
    adapter (job["source"]) rather than the display label, so the
    numbers join cleanly with the ranking output.
    """
    discovered = Counter()

    for result in provider_results:
        for job in result.get("jobs") or []:
            discovered[
                str(job.get("source") or "unknown")
            ] += 1

    enriched = Counter(
        str(job.get("source") or "unknown")
        for job in ranked
    )

    qualified = Counter(
        str(job.get("source") or "unknown")
        for job in ranked
        if job_qualification(job) == QUALIFIED
    )

    possible = Counter(
        str(job.get("source") or "unknown")
        for job in ranked
        if job_qualification(job) == POSSIBLE_MATCH
    )

    verified = Counter(
        str(job.get("source") or "unknown")
        for job in ranked
        if job.get("verification_status") == "VERIFIED"
    )

    rows = []

    for source in sorted(
        set(discovered) | set(enriched),
        key=lambda name: discovered.get(name, 0),
        reverse=True,
    ):
        keep = enriched.get(source, 0)

        rows.append(
            {
                "source": source,
                "discovered": discovered.get(source, 0),
                "enriched": keep,
                "verified": verified.get(source, 0),
                "eligible": qualified.get(source, 0),
                "qualified": qualified.get(source, 0),
                "possible_matches": possible.get(source, 0),
                "relevance_rate_enriched": (
                    round(
                        qualified.get(source, 0) / keep,
                        4,
                    )
                    if keep
                    else 0.0
                ),
                "relevance_rate_discovered": (
                    round(
                        qualified.get(source, 0)
                        / discovered.get(source, 0),
                        4,
                    )
                    if discovered.get(source, 0)
                    else 0.0
                ),
            }
        )

    return rows


# ============================================================
# QUERY QUALITY
# ============================================================

def query_quality(ranked):
    """Per-search-query enriched/qualified relevance metrics."""
    buckets = defaultdict(
        lambda: {"enriched": 0, "qualified": 0, "possible": 0}
    )

    for job in ranked:
        key = str(job.get("search_query") or "(no query)")

        buckets[key]["enriched"] += 1

        qualification = job_qualification(job)

        if qualification == POSSIBLE_MATCH:
            buckets[key]["possible"] += 1
        elif qualification == QUALIFIED:
            buckets[key]["qualified"] += 1

    rows = []

    for query, counts in buckets.items():
        rows.append(
            {
                "search_query": query,
                "family": query_family_for(query),
                "enriched": counts["enriched"],
                "eligible": counts["qualified"],
                "qualified": counts["qualified"],
                "possible_matches": counts["possible"],
                "relevance_rate": (
                    round(
                        counts["qualified"]
                        / counts["enriched"],
                        4,
                    )
                    if counts["enriched"]
                    else 0.0
                ),
            }
        )

    return sorted(
        rows,
        key=lambda row: (
            row["qualified"],
            row["enriched"],
        ),
        reverse=True,
    )


# ============================================================
# SOURCE OVERLAP
# ============================================================

def source_overlap(ranked):
    """Cross-provider overlap from jobs kept by the dedupe layer.

    Each kept job records which other sources reported the same
    underlying listing in ``duplicate_sources``. Pair counts reveal
    which providers genuinely share jobs.
    """
    pair_counts = Counter()

    for job in ranked:
        source = str(job.get("source") or "unknown")

        for duplicate in (
            job.get("duplicate_sources") or []
        ):
            pair = tuple(sorted((source, duplicate)))
            pair_counts[pair] += 1

    return [
        {
            "source_a": source_a,
            "source_b": source_b,
            "overlap_count": count,
        }
        for (source_a, source_b), count in
        pair_counts.most_common()
    ]


# ============================================================
# FUNNEL
# ============================================================

def build_funnel(
    provider_results,
    total_discovered,
    unique_jobs,
    enriched_jobs,
    ranked_jobs,
    qualified_jobs,
    possible_matches,
    new_jobs,
    prefilter_counts,
):
    """Return the full funnel report (every stage, no double count)."""
    enriched_ids = {
        job_identity(job)
        for job in enriched_jobs
    }

    enrichment_skipped = 0
    skipped_by_source = Counter()

    for job in unique_jobs:
        if job_identity(job) not in enriched_ids:
            enrichment_skipped += 1
            skipped_by_source[
                str(job.get("source") or "unknown")
            ] += 1

    verified_count = sum(
        1
        for job in enriched_jobs
        if job.get("verification_status") == "VERIFIED"
    )

    unverified_count = (
        len(enriched_jobs) - verified_count
    )

    stages = stage_counter(
        ranked_jobs
    )

    dedupe_pairs = source_overlap(
        ranked_jobs
    )

    qualified_count = len(
        qualified_jobs
    )

    rejected_count = sum(
        count
        for stage, count in stages.items()
        if stage in REJECTION_STAGES
    )

    return {
        "stages": {
            "discovered": total_discovered,
            "normalized_unique": len(unique_jobs),
            "duplicates": (
                total_discovered - len(unique_jobs)
            ),
            "duplicates_removed": (
                total_discovered - len(unique_jobs)
            ),
            "prefilter_pass": prefilter_counts.get(
                True, 0
            ),
            "prefilter_rejected": prefilter_counts.get(
                False, 0
            ),
            "prefilter_rejected_priority_only": (
                prefilter_counts.get(False, 0)
            ),
            "enrichment_skipped": enrichment_skipped,
            "enriched": len(enriched_jobs),
            "verified": verified_count,
            "unverified": unverified_count,
            "qualified": qualified_count,
            "possible_matches": len(possible_matches),
            "eligible": qualified_count,
            "rejected": rejected_count,
            "already_sent": (
                qualified_count - len(new_jobs)
            ),
            "new_telegram": len(new_jobs),
        },
        "enrichment_skipped_by_source": dict(
            sorted(
                skipped_by_source.items(),
                key=lambda item: item[1],
                reverse=True,
            )
        ),
        "rejected_stages": dict(
            sorted(
                {
                    stage: count
                    for stage, count in stages.items()
                    if stage in REJECTION_STAGES
                }.items(),
                key=lambda item: item[1],
                reverse=True,
            )
        ),
        "eligible_by_provider": {},
        "source_overlap": dedupe_pairs,
        "notes": (
            "qualified = no hard filter reason AND score >= "
            "MINIMUM_SCORE; possible_match = no hard filter reason "
            "but score below the gate (never sent, kept for analysis); "
            "rejected = hard filter reason (always wins over score). "
            "enrichment_skipped splits into jobs below the priority "
            "bar and jobs beyond the cap; import the prefilter_skipped "
            "report (JOB_AGENT_SAVE_SKIPPED=1) for per-job detail. "
            "source_overlap only sees kept jobs, so same-source "
            "duplicate removals are not pairs."
        ),
    }