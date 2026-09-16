"""Collect, dedupe, enrich, rank, filter and prepare jobs for Telegram.

Pipeline:

    MANY JOB SOURCES
        -> BROAD DISCOVERY
        -> NORMALIZE
        -> GLOBAL DEDUPE
        -> FULL JOB DETAILS / JD ENRICHMENT
        -> PROFILE MATCHING
        -> RANKING
        -> SENT HISTORY
        -> REPORTS / TELEGRAM DATA
"""

import json
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import adaptive_query
import source_discovery
import source_runner
from ai_config import (
    MAX_SEARCH_ROUNDS,
    MAX_SOURCE_LOOKUPS,
    SOURCE_DISCOVERY_ENABLED,
    adaptive_discovery_enabled,
)
from canonical import deduplicate_jobs, job_identity
from job_enricher import enrich_jobs
from job_matcher import (
    QUALIFIED,
    enrichment_priority,
    get_rejected_jobs,
    job_priority_tier,
    job_qualification,
    job_rank_key,
    keep_possible_matches,
    keep_relevant_jobs,
    near_miss_score_from_details,
    prefilter_job,
    rank_jobs,
)
from sources.base import build_locations, build_search_queries
from funnel import (
    build_funnel,
    provider_quality,
    query_quality,
    rejection_stage,
    source_overlap,
    stage_counter,
)


# Reports always resolve against the repository root, never the
# current working directory, so local and CI runs share one
# deterministic report + sent-history location.
JOBS_DIR = Path(__file__).resolve().parent
REPO_ROOT = JOBS_DIR.parent

OUTPUT_DIR = REPO_ROOT / "reports"

OUTPUT_FILE = OUTPUT_DIR / "jobs.json"
FULL_OUTPUT_FILE = OUTPUT_DIR / "all_ranked_jobs.json"
REJECTED_OUTPUT_FILE = OUTPUT_DIR / "rejected_jobs.json"
UNVERIFIED_OUTPUT_FILE = OUTPUT_DIR / "unverified_jobs.json"
POSSIBLE_OUTPUT_FILE = OUTPUT_DIR / "possible_matches.json"
SENT_FILE = OUTPUT_DIR / "sent_jobs.json"
SOURCE_STATS_FILE = OUTPUT_DIR / "source_stats.json"
PROVIDER_HEALTH_FILE = OUTPUT_DIR / "provider_health.json"
RUN_SUMMARY_FILE = OUTPUT_DIR / "run_summary.json"
FUNNEL_FILE = OUTPUT_DIR / "funnel.json"
SKIPPED_FILE = OUTPUT_DIR / "prefilter_skipped.json"

_PRIORITY_ORDER = {
    "P1": 0,
    "P2": 1,
    "P3": 2,
    "None": 3,
}


def _priority_sort(item):
    return _PRIORITY_ORDER.get(
        item[0], 99
    )

DEFAULT_ENRICH_CAP = 300


def load_sent_jobs():
    """Load previously sent job identities."""
    if not SENT_FILE.exists():
        return set()

    try:

        with open(
            SENT_FILE,
            "r",
            encoding="utf-8",
        ) as file:

            data = json.load(file)

        if isinstance(
            data,
            list,
        ):
            return set(data)

        return set()

    except (
        json.JSONDecodeError,
        OSError,
    ):

        return set()


def save_sent_jobs(sent_jobs):
    """Save previously sent job identities."""
    OUTPUT_DIR.mkdir(
        exist_ok=True
    )

    with open(
        SENT_FILE,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            sorted(sent_jobs),
            file,
            indent=2,
            ensure_ascii=False,
        )


def save_json(path, data):
    """Save JSON report."""
    OUTPUT_DIR.mkdir(
        exist_ok=True
    )

    with open(
        path,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            data,
            file,
            indent=2,
            ensure_ascii=False,
        )


def is_detail_verified(job):
    """Determine whether the actual job page was fetched."""
    verification = job.get(
        "detail_verification",
        {},
    )

    if not isinstance(
        verification,
        dict,
    ):
        return False

    return bool(
        verification.get(
            "success",
            False,
        )
    )


def get_match_details(job):
    """Safely return matcher details."""
    details = job.get(
        "match_details",
        {},
    )

    if not isinstance(
        details,
        dict,
    ):
        return {}

    return details


def new_qualified_jobs(ranked_jobs, sent_jobs):
    """Return new + qualified jobs and mark them as sent.

    Telegram sends ONLY jobs that are new (not in sent history) AND
    qualified (no hard rejection, score >= MINIMUM_SCORE). Possible
    matches and hard-rejected jobs are never selected, and the
    identity is recorded so a later run never duplicates the alert.
    """
    new_jobs = []

    for job in ranked_jobs:

        if job_qualification(job) != QUALIFIED:
            continue

        identity = job_identity(
            job
        )

        if not identity:
            continue

        if identity in sent_jobs:
            continue

        new_jobs.append(
            job
        )

        sent_jobs.add(
            identity
        )

    return new_jobs


def main():

    OUTPUT_DIR.mkdir(
        exist_ok=True
    )

    print()
    print("=" * 70)
    print("SIVA JOB AGENT - MULTI-SOURCE JOB DISCOVERY")
    print("=" * 70)

    # --------------------------------------------------------
    # 1. SEARCH TERMS + LOCATIONS FROM profile.py
    # --------------------------------------------------------

    query_cap = _int_or_none(
        os.environ.get("JOB_AGENT_QUERIES")
    )

    search_queries = build_search_queries(
        limit=query_cap
    )

    locations = build_locations()

    print()
    print(
        f"Search queries : {len(search_queries)}"
    )

    print(
        f"Locations      : "
        f"{', '.join(locations)}"
    )

    # --------------------------------------------------------
    # 2. DISCOVERY (adaptive multi-round)
    # --------------------------------------------------------

    print()
    print(
        "[1/7] Running round 1 source providers..."
    )

    (
        provider_results,
        unique_jobs,
        stats,
    ) = source_runner.run_sources(
        search_queries=search_queries,
        locations=locations,
    )

    total_discovered = sum(
        result.get("count", 0)
        for result in provider_results
    )

    discovery_rounds = [
        {
            "round": 1,
            "queries": len(search_queries),
            "discovered": total_discovered,
            "unique": len(unique_jobs),
            "new_unique": len(unique_jobs),
            "by_priority": adaptive_query.analyze_round(
                unique_jobs
            )["by_priority"],
        }
    ]

    source_runner.print_source_breakdown(
        provider_results,
        unique_jobs,
        [
            job
            for job in run_all_jobs(provider_results)
        ],
    )

    # Adaptive extra rounds: deterministic profile vocabulary (never an
    # LLM) that targets only tiers underrepresented after the previous
    # round. Rounds are merged with the global dedupe so a job found in
    # two rounds collapses into one with round-1 attribution.
    round_slots = [
        adaptive_query.attribution_slots(
            search_queries,
            1,
        )
    ]
    assigned_queries = list(search_queries)

    if (
        adaptive_discovery_enabled()
        and MAX_SEARCH_ROUNDS > 1
    ):
        current_round = 1
        pool_before = len(unique_jobs)

        while current_round < MAX_SEARCH_ROUNDS:
            analysis = adaptive_query.analyze_round(
                unique_jobs
            )

            underrepresented = (
                adaptive_query.underrepresented_tiers(
                    Counter(
                        analysis["by_priority"]
                    ),
                    analysis["total"],
                )
            )

            if not underrepresented:
                break

            next_queries = adaptive_query.round2_queries(
                assigned_queries,
                underrepresented,
            )

            if not next_queries:
                break

            next_query_text = [
                query
                for query, family in next_queries
            ]

            current_round += 1

            print()
            print(
                f"[1/7] Adaptive round {current_round} - "
                f"underrepresented tier(s): "
                f"{', '.join(f'P{t}' for t in underrepresented)}"
            )
            print(
                f"      Additional queries  : "
                f"{len(next_query_text)}"
            )

            before_ids = {
                job_identity(job)
                for job in unique_jobs
            }

            (
                round_provider_results,
                round_unique_jobs,
                _round_stats,
            ) = source_runner.run_sources(
                search_queries=next_query_text,
                locations=locations,
            )

            round_discovered = sum(
                result.get("count", 0)
                for result in round_provider_results
            )

            round_slots.append(
                adaptive_query.build_round2_slots(
                    next_queries,
                    current_round,
                )
            )
            assigned_queries.extend(
                next_query_text
            )

            merged_unique = deduplicate_jobs(
                list(unique_jobs)
                + run_all_jobs(
                    round_provider_results
                )
            )

            new_uniques = (
                len(merged_unique)
                - len(unique_jobs)
            )

            unique_jobs = merged_unique

            discovery_rounds.append(
                {
                    "round": current_round,
                    "queries": len(
                        next_query_text
                    ),
                    "discovered": (
                        round_discovered
                    ),
                    "unique": len(
                        round_unique_jobs
                    ),
                    "new_unique": new_uniques,
                    "by_priority": (
                        adaptive_query.analyze_round(
                            round_unique_jobs
                        )[
                            "by_priority"
                        ]
                    ),
                }
            )

            print(
                f"      Round discovered   : "
                f"{round_discovered}"
            )
            print(
                f"      Round unique       : "
                f"{len(round_unique_jobs)}"
            )
            print(
                f"      New unique added   : "
                f"{new_uniques}"
            )

            if new_uniques == 0:
                break

        print()
        print(
            f"[1/7] Discovery finished after "
            f"{current_round} round(s); "
            f"total unique {len(unique_jobs)} "
            f"(adaptive added "
            f"{len(unique_jobs) - pool_before})."
        )

    # Attribution: every discovered job keeps (query, query_family,
    # priority, provider, discovery_round) for the reports.
    attribution_by_query = adaptive_query.stamp_attribution(
        unique_jobs,
        *round_slots,
    )

    # --------------------------------------------------------
    # 3. GLOBAL DEDUPE (final summary across rounds)
    # --------------------------------------------------------

    print()
    print(
        "[2/7] Global deduplication across providers..."
    )

    print(
        f"       Total discovered : "
        f"{total_discovered}"
    )

    print(
        f"       Total unique     : "
        f"{len(unique_jobs)}"
    )

    # --------------------------------------------------------
    # 3b. SOURCE DISCOVERY (optional, additive metadata only)
    # --------------------------------------------------------

    source_discovery_report = {
        "status": "disabled",
        "reason": (
            "JOB_AGENT_SOURCE_DISCOVERY not enabled"
        ),
        "lookups": 0,
        "successful": 0,
        "new_candidates": 0,
        "ats_detected": {},
        "approved": [],
        "rejected": [],
        "pending_review": [],
    }

    if SOURCE_DISCOVERY_ENABLED:
        final_analysis = adaptive_query.analyze_round(
            unique_jobs
        )

        underrepresented = (
            adaptive_query.underrepresented_tiers(
                Counter(
                    final_analysis["by_priority"]
                ),
                final_analysis["total"],
            )
        )

        if not underrepresented:
            source_discovery_report["reason"] = (
                "no underrepresented tier "
                "after adaptive rounds"
            )
        else:
            print()
            print(
                "[2/7] Probing public career/ATS "
                f"sources ({len(assigned_queries)} "
                f"queries, budget "
                f"{MAX_SOURCE_LOOKUPS})..."
            )

            status, candidates, error = (
                source_discovery.discover_sources(
                    assigned_queries,
                )
            )

            classification = (
                source_discovery.classify_candidates(
                    candidates
                )
            )

            source_discovery_report.update(
                {
                    "status": status,
                    "reason": error,
                    "lookups": len(candidates),
                    "successful": len(candidates),
                    "new_candidates": len(candidates),
                    "ats_detected": classification[
                        "ats_detected"
                    ],
                    "approved": classification[
                        "approved"
                    ],
                    "rejected": classification[
                        "rejected"
                    ],
                    "pending_review": (
                        classification[
                            "pending_review"
                        ][:10]
                    ),
                }
            )

            print(
                f"      Source discovery  : "
                f"{status}"
            )
            print(
                f"      Candidates        : "
                f"{len(candidates)}"
            )

    # --------------------------------------------------------
    # 4. ENRICH
    # --------------------------------------------------------

    enriched_cap = _int_or_none(
        os.environ.get("JOB_AGENT_MAX_ENRICH")
    )

    if enriched_cap is None:
        enriched_cap = DEFAULT_ENRICH_CAP

    enrichable = _stratified_jobs(
        unique_jobs,
        enriched_cap,
    )

    # Cheap conservative pre-filter (never a hard gate). Counted for
    # the funnel so we can see how many unique listings have any
    # plausible relevance signal before full-page enrichment.
    prefilter_counts = Counter(
        bool(prefilter_job(job))
        for job in unique_jobs
    )

    print()
    print(
        "[3/7] Fetching full available job details..."
    )

    enriched_jobs = enrich_jobs(
        enrichable
    )

    verified_count = sum(
        1
        for job in enriched_jobs
        if is_detail_verified(job)
    )

    unverified_count = (
        len(enriched_jobs)
        - verified_count
    )

    print(
        f"       Detail verified  : "
        f"{verified_count}"
    )

    print(
        f"       Detail unverified: "
        f"{unverified_count}"
    )

    # --------------------------------------------------------
    # 5. RANK
    # --------------------------------------------------------

    print()
    print(
        "[4/7] Running deep job matching..."
    )

    ranked_jobs = rank_jobs(
        enriched_jobs
    )

    for job in ranked_jobs:
        job["rejection_stage"] = rejection_stage(job)

    # --------------------------------------------------------
    # 6. FILTER
    # --------------------------------------------------------

    qualified_jobs = (
        keep_relevant_jobs(
            ranked_jobs
        )
    )

    possible_matches = (
        keep_possible_matches(
            ranked_jobs
        )
    )

    rejected_jobs = (
        get_rejected_jobs(
            ranked_jobs
        )
    )

    unverified_jobs = []

    for job in ranked_jobs:

        details = get_match_details(
            job
        )

        verification_status = (
            details.get(
                "verification_status"
            )
        )

        if (
            verification_status
            == "UNVERIFIED"
        ):
            unverified_jobs.append(
                job
            )

            continue

        if not is_detail_verified(
            job
        ):
            unverified_jobs.append(
                job
            )

    # --------------------------------------------------------
    # 7. SENT HISTORY
    # --------------------------------------------------------

    print()
    print(
        "[5/7] Checking previously sent jobs..."
    )

    sent_jobs = load_sent_jobs()

    new_jobs = new_qualified_jobs(
        ranked_jobs,
        sent_jobs,
    )

    save_sent_jobs(
        sent_jobs
    )

    # --------------------------------------------------------
    # 8. SAVE REPORTS
    # --------------------------------------------------------

    save_json(
        OUTPUT_FILE,
        new_jobs,
    )

    save_json(
        FULL_OUTPUT_FILE,
        ranked_jobs,
    )

    save_json(
        REJECTED_OUTPUT_FILE,
        rejected_jobs,
    )

    save_json(
        UNVERIFIED_OUTPUT_FILE,
        unverified_jobs,
    )

    save_json(
        POSSIBLE_OUTPUT_FILE,
        possible_matches,
    )

    stats["summary"].update(
        {
            "total_discovered": total_discovered,
            "total_unique": len(unique_jobs),
            "total_enriched": len(enriched_jobs),
            "total_verified": verified_count,
            "total_unverified": unverified_count,
            "total_qualified": len(qualified_jobs),
            "total_eligible": len(qualified_jobs),
            "total_possible_matches": len(possible_matches),
            "total_rejected": len(rejected_jobs),
            "total_new_telegram": len(new_jobs),
            "run_at_utc": (
                datetime.now(timezone.utc)
                .isoformat(timespec="seconds")
            ),
        }
    )

    save_json(
        SOURCE_STATS_FILE,
        stats,
    )

    save_json(
        PROVIDER_HEALTH_FILE,
        stats.get(
            "provider_health",
            [],
        ),
    )

    # --------------------------------------------------------
    # 8b. RUN SUMMARY (funnel, provider/query quality, near-misses)
    # --------------------------------------------------------

    qualified_by_provider = {}

    for job in qualified_jobs:
        source = str(job.get("source") or "unknown")
        qualified_by_provider[source] = (
            qualified_by_provider.get(source, 0) + 1
        )

    possible_by_provider = {}

    for job in possible_matches:
        source = str(job.get("source") or "unknown")
        possible_by_provider[source] = (
            possible_by_provider.get(source, 0) + 1
        )

    # --------------------------------------------------------
    # PRIORITY BREAKDOWN (P1 support / P2 QA / P3 dev)
    # --------------------------------------------------------

    def _tier_or_none(job):
        return (
            job_priority_tier(job)
            or "None"
        )

    discovered_by_priority = Counter(
        _tier_or_none(job)
        for job in unique_jobs
    )

    enriched_by_priority = Counter(
        _tier_or_none(job)
        for job in enriched_jobs
    )

    qualified_by_priority = Counter(
        _tier_or_none(job)
        for job in qualified_jobs
    )

    possible_by_priority = Counter(
        _tier_or_none(job)
        for job in possible_matches
    )

    new_by_priority = Counter(
        _tier_or_none(job)
        for job in new_jobs
    )

    top_jobs_by_priority = {}

    for tier in ("P1", "P2", "P3"):
        tier_jobs = [
            job
            for job in qualified_jobs
            if job_priority_tier(job) == tier
        ]

        tier_jobs.sort(
            key=job_rank_key,
            reverse=True,
        )

        top_jobs_by_priority[tier] = [
            {
                "title": job.get("title"),
                "company": job.get("company"),
                "source": job.get("source"),
                "url": (
                    job.get("url")
                    or job.get("job_url")
                ),
                "location": job.get("location"),
                "match_score": job.get(
                    "match_score"
                ),
                "rank_score": job.get(
                    "rank_score"
                ),
                "job_family": job.get(
                    "job_family"
                ),
                "priority_tier": job.get(
                    "priority_tier"
                ),
            }
            for job in tier_jobs[:5]
        ]

    rejection_counts = Counter()

    for job in rejected_jobs:
        details = get_match_details(job)
        reasons = details.get("filter_reasons") or []

        if not reasons:
            rejection_counts["(no reason recorded)"] += 1
        else:
            for reason in reasons:
                rejection_counts[reason] += 1

    rejected_stage_counts = stage_counter(
        rejected_jobs
    )

    funnel_report = build_funnel(
        provider_results=provider_results,
        total_discovered=total_discovered,
        unique_jobs=unique_jobs,
        enriched_jobs=enriched_jobs,
        ranked_jobs=ranked_jobs,
        qualified_jobs=qualified_jobs,
        possible_matches=possible_matches,
        new_jobs=new_jobs,
        prefilter_counts=prefilter_counts,
    )

    funnel_report["eligible_by_provider"] = qualified_by_provider
    funnel_report["possible_matches_by_provider"] = possible_by_provider

    save_json(
        FUNNEL_FILE,
        funnel_report,
    )

    top_false_negatives = []

    for job in rejected_jobs:
        details = get_match_details(job)

        near_miss = near_miss_score_from_details(details)

        if near_miss < 20:
            continue

        top_false_negatives.append(
            {
                "title": job.get("title"),
                "company": job.get("company"),
                "source": job.get("source"),
                "url": (
                    job.get("url")
                    or job.get("job_url")
                ),
                "location": job.get("location"),
                "match_score": job.get("match_score"),
                "near_miss_score": near_miss,
                "rejection_stage": job.get(
                    "rejection_stage"
                ),
                "filter_reasons": details.get(
                    "filter_reasons"
                ),
                "matched_roles": details.get(
                    "matched_roles"
                ),
                "matched_skills": details.get(
                    "matched_skills"
                ),
                "semantic_score": details.get(
                    "semantic_score"
                ),
            }
        )

    top_false_negatives.sort(
        key=lambda item: item["near_miss_score"],
        reverse=True,
    )

    if os.environ.get("JOB_AGENT_SAVE_SKIPPED", "").lower() in {
        "1",
        "true",
        "yes",
    }:
        enriched_ids = {
            job_identity(job)
            for job in enriched_jobs
        }

        skipped = []

        for job in unique_jobs:
            identity = job_identity(job)

            if identity in enriched_ids:
                continue

            skipped.append(
                {
                    "source": job.get("source"),
                    "source_job_id": job.get(
                        "source_job_id"
                    ),
                    "title": job.get("title"),
                    "company": job.get("company"),
                    "location": job.get("location"),
                    "url": (
                        job.get("url")
                        or job.get("job_url")
                    ),
                    "search_query": job.get(
                        "search_query"
                    ),
                    "enrichment_priority": enrichment_priority(
                        job
                    ),
                    "prefilter": bool(
                        prefilter_job(job)
                    ),
                    "rejection_stage": (
                        "enrichment_skipped"
                    ),
                }
            )

        skipped.sort(
            key=lambda item: item[
                "enrichment_priority"
            ],
            reverse=True,
        )

        save_json(
            SKIPPED_FILE,
            skipped,
        )

    query_quality_rows = query_quality(
        ranked_jobs
    )

    for row in query_quality_rows:
        slot = attribution_by_query.get(
            str(
                row.get("search_query") or ""
            ).strip().lower()
        )

        if slot is None:
            continue

        row["query_family"] = slot.get(
            "query_family"
        )
        row["priority"] = slot.get("priority")
        row["discovery_round"] = slot.get(
            "discovery_round"
        )

    run_summary = {
        "run_at_utc": stats["summary"].get("run_at_utc"),
        "totals": dict(stats["summary"]),
        "discovered_by_priority": dict(
            sorted(
                discovered_by_priority.items(),
                key=_priority_sort,
            )
        ),
        "enriched_by_priority": dict(
            sorted(
                enriched_by_priority.items(),
                key=_priority_sort,
            )
        ),
        "qualified_by_priority": dict(
            sorted(
                qualified_by_priority.items(),
                key=_priority_sort,
            )
        ),
        "possible_matches_by_priority": dict(
            sorted(
                possible_by_priority.items(),
                key=_priority_sort,
            )
        ),
        "new_telegram_by_priority": dict(
            sorted(
                new_by_priority.items(),
                key=_priority_sort,
            )
        ),
        "top_jobs_by_priority": top_jobs_by_priority,
        "eligible_by_provider": dict(
            sorted(
                qualified_by_provider.items(),
                key=lambda item: item[1],
                reverse=True,
            )
        ),
        "qualified_by_provider": dict(
            sorted(
                qualified_by_provider.items(),
                key=lambda item: item[1],
                reverse=True,
            )
        ),
        "possible_matches_by_provider": dict(
            sorted(
                possible_by_provider.items(),
                key=lambda item: item[1],
                reverse=True,
            )
        ),
        "rejected_stages": dict(
            sorted(
                dict(rejected_stage_counts).items(),
                key=lambda item: item[1],
                reverse=True,
            )
        ),
        "top_possible_false_negatives": (
            top_false_negatives[:25]
        ),
        "provider_quality": provider_quality(
            provider_results,
            ranked_jobs,
        ),
        "query_quality": query_quality_rows,
        "discovery_rounds": discovery_rounds,
        "source_discovery": source_discovery_report,
        "source_overlap": funnel_report[
            "source_overlap"
        ],
        "top_rejection_reasons": [
            {"count": count, "reason": reason}
            for reason, count in rejection_counts.most_common(20)
        ],
    }

    save_json(
        RUN_SUMMARY_FILE,
        run_summary,
    )

    # --------------------------------------------------------
    # 9. REPORT
    # --------------------------------------------------------

    print()
    print(
        "[6/7] Reports saved."
    )

    print()
    print("=" * 70)
    print("V1.1 RESULTS")
    print("=" * 70)

    totals = [
        ("TOTAL DISCOVERED", total_discovered),
        ("TOTAL UNIQUE", len(unique_jobs)),
        ("TOTAL ENRICHED", len(enriched_jobs)),
        ("TOTAL VERIFIED", verified_count),
        ("TOTAL UNVERIFIED", unverified_count),
        ("TOTAL QUALIFIED", len(qualified_jobs)),
        ("TOTAL POSSIBLE MATCHES", len(possible_matches)),
        ("TOTAL REJECTED", len(rejected_jobs)),
        ("TOTAL NEW TELEGRAM", len(new_jobs)),
    ]

    for label, value in totals:
        print(f"{label:18} : {value}")

    print()
    print("DISCOVERY ROUNDS")

    for entry in discovery_rounds:
        by_priority = entry.get("by_priority") or {}
        tiers = (
            f"P1={by_priority.get('P1', 0)} "
            f"P2={by_priority.get('P2', 0)} "
            f"P3={by_priority.get('P3', 0)}"
        )
        print(
            f"Round {entry.get('round')}: "
            f"{entry.get('queries')} queries / "
            f"{entry.get('discovered')} discovered / "
            f"{entry.get('unique')} unique "
            f"(+{entry.get('new_unique')} new) "
            f"| {tiers}"
        )

    if SOURCE_DISCOVERY_ENABLED:
        print()
        print(
            f"SOURCE DISCOVERY    : "
            f"{source_discovery_report.get('status')}"
        )
        print(
            f"  candidates        : "
            f"{source_discovery_report.get('new_candidates')}"
        )
        print(
            f"  ats detected      : "
            f"{source_discovery_report.get('ats_detected') or {}}"
        )

    stages = funnel_report["stages"]

    print()
    print(
        f"Prefilter signal  : "
        f"{stages['prefilter_pass']} pass / "
        f"{stages['prefilter_rejected_priority_only']} "
        f"low-signal"
    )

    print(
        f"Enrichment skipped: "
        f"{stages['enrichment_skipped']}"
    )

    rejected_stages = funnel_report[
        "rejected_stages"
    ]

    if rejected_stages:
        print(
            "Rejected stages   : "
            + ", ".join(
                f"{stage}={count}"
                for stage, count in
                rejected_stages.items()
            )
        )

    print()
    print(
        "QUALIFIED BY PRIORITY"
    )

    for tier in ("P1", "P2", "P3"):
        print(
            f"{tier}                : "
            f"{qualified_by_priority.get(tier, 0)}"
        )

    if new_jobs:
        print()
        print(
            "NEW TELEGRAM BY PRIORITY"
        )

        for tier in ("P1", "P2", "P3"):
            tier_count = (
                new_by_priority.get(tier, 0)
            )

            if tier_count:
                print(
                    f"{tier}                : {tier_count}"
                )

    print()
    print(
        "Reports created:"
    )

    for report in (
        OUTPUT_FILE,
        FULL_OUTPUT_FILE,
        REJECTED_OUTPUT_FILE,
        UNVERIFIED_OUTPUT_FILE,
        POSSIBLE_OUTPUT_FILE,
        SOURCE_STATS_FILE,
        PROVIDER_HEALTH_FILE,
        RUN_SUMMARY_FILE,
        FUNNEL_FILE,
        SENT_FILE,
    ):
        print(f"  - {report}")

    print()
    print("=" * 70)
    print("PIPELINE COMPLETE")
    print("=" * 70)


def run_all_jobs(provider_results):
    """Yield every raw job from every provider result."""
    all_jobs = []

    for result in provider_results:
        all_jobs.extend(
            result.get("jobs", [])
        )

    return all_jobs


def _stratified_jobs(unique_jobs, cap):
    """Pick up to ``cap`` jobs for enrichment.

    Combines two goals:

    1. DIVERSITY - the cap is never swallowed by the largest
       providers or a single search query, and both remote and
       India-city postings get represented.
    2. PRIORITY - inside every (source, location, query) bucket the
       jobs with the strongest cheap relevance signal are picked
       first, so the cap is spent where it has the most signal.

    Buckets are interleaved round-robin so every bucket gets a fair
    share while still filling the cap at one job per sweep.
    """
    from collections import defaultdict

    priorities = {
        id(job): enrichment_priority(job)
        for job in unique_jobs
    }

    buckets = defaultdict(list)

    for job in unique_jobs:
        source = job.get("source") or "unknown"
        location_bucket = _location_bucket(job)
        query = job.get("search_query") or "(no query)"
        buckets[(source, location_bucket, query)].append(job)

    for bucket_jobs in buckets.values():
        bucket_jobs.sort(
            key=lambda job: priorities[id(job)],
            reverse=True,
        )

    ordered_keys = sorted(
        buckets,
        key=lambda key: (
            -priorities[id(buckets[key][0])],
            key,
        ),
    )

    selected = []
    cursor = {key: 0 for key in ordered_keys}
    count = 0

    while count < cap:
        progressed = False

        for key in ordered_keys:
            bucket = buckets[key]
            index = cursor[key]

            if index >= len(bucket):
                continue

            selected.append(bucket[index])
            cursor[key] = index + 1
            count += 1
            progressed = True

            if count >= cap:
                break

        if not progressed:
            break

    return selected


def _location_bucket(job):
    """Classify a raw listing as remote / india-city / other."""
    text = " ".join(
        str(job.get(field) or "")
        for field in (
            "location",
            "work_mode",
            "remote_work_model",
        )
    ).lower()

    if any(
        alias in text
        for alias in (
            "remote",
            "work from home",
            "wfh",
            "anywhere",
        )
    ):
        return "remote"

    if any(
        alias in text
        for alias in (
            "chennai",
            "bangalore",
            "bengaluru",
            "hyderabad",
            "coimbatore",
            "tamil nadu",
            "karnataka",
            "telangana",
        )
    ):
        return "city"

    return "other"


def _int_or_none(value):
    if not value:
        return None

    try:
        return int(value)
    except ValueError:
        return None


if __name__ == "__main__":
    main()