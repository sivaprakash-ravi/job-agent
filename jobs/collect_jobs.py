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

import source_runner
from canonical import job_identity
from job_enricher import enrich_jobs
from job_matcher import (
    get_rejected_jobs,
    keep_relevant_jobs,
    prioritize_for_enrichment,
    rank_jobs,
)
from sources.base import build_locations, build_search_queries


OUTPUT_DIR = Path("reports")

OUTPUT_FILE = OUTPUT_DIR / "jobs.json"
FULL_OUTPUT_FILE = OUTPUT_DIR / "all_ranked_jobs.json"
REJECTED_OUTPUT_FILE = OUTPUT_DIR / "rejected_jobs.json"
UNVERIFIED_OUTPUT_FILE = OUTPUT_DIR / "unverified_jobs.json"
SENT_FILE = OUTPUT_DIR / "sent_jobs.json"
SOURCE_STATS_FILE = OUTPUT_DIR / "source_stats.json"
PROVIDER_HEALTH_FILE = OUTPUT_DIR / "provider_health.json"
RUN_SUMMARY_FILE = OUTPUT_DIR / "run_summary.json"

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
    # 2. DISCOVERY
    # --------------------------------------------------------

    print()
    print(
        "[1/7] Running all source providers..."
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

    source_runner.print_source_breakdown(
        provider_results,
        unique_jobs,
        [
            job
            for job in run_all_jobs(provider_results)
        ],
    )

    # --------------------------------------------------------
    # 3. GLOBAL DEDUPE
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

    print()
    print(
        "[3/7] Fetching full available job details..."
    )

    # Cheap pre-filter: enrich likely-relevant jobs first so the
    # enrichment cap is spent where it has the most signal. The
    # remainder is still enriched whenever cap allows, preserving
    # recall on thin raw listings.
    likely_relevant, rest = prioritize_for_enrichment(
        enrichable
    )

    enriched_jobs = enrich_jobs(
        likely_relevant
    )

    remaining_cap = enriched_cap - len(likely_relevant)

    if remaining_cap > 0 and rest:
        enriched_jobs.extend(
            enrich_jobs(
                rest[:remaining_cap]
            )
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

    # --------------------------------------------------------
    # 6. FILTER
    # --------------------------------------------------------

    relevant_jobs = (
        keep_relevant_jobs(
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

    new_jobs = []

    for job in relevant_jobs:

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

    stats["summary"].update(
        {
            "total_discovered": total_discovered,
            "total_unique": len(unique_jobs),
            "total_enriched": len(enriched_jobs),
            "total_verified": verified_count,
            "total_unverified": unverified_count,
            "total_eligible": len(relevant_jobs),
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
    # 8b. RUN SUMMARY (provider health + rejection reasons)
    # --------------------------------------------------------

    eligible_by_provider = {}

    for job in relevant_jobs:
        source = str(job.get("source") or "unknown")
        eligible_by_provider[source] = (
            eligible_by_provider.get(source, 0) + 1
        )

    rejection_counts = Counter()

    for job in rejected_jobs:
        details = get_match_details(job)
        reasons = details.get("filter_reasons") or []

        if not reasons:
            rejection_counts["(no reason recorded)"] += 1
        else:
            for reason in reasons:
                rejection_counts[reason] += 1

    run_summary = {
        "run_at_utc": stats["summary"].get("run_at_utc"),
        "totals": dict(stats["summary"]),
        "eligible_by_provider": dict(
            sorted(
                eligible_by_provider.items(),
                key=lambda item: item[1],
                reverse=True,
            )
        ),
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
    print("V1 RESULTS")
    print("=" * 70)

    totals = [
        ("TOTAL DISCOVERED", total_discovered),
        ("TOTAL UNIQUE", len(unique_jobs)),
        ("TOTAL ENRICHED", len(enriched_jobs)),
        ("TOTAL VERIFIED", verified_count),
        ("TOTAL UNVERIFIED", unverified_count),
        ("TOTAL ELIGIBLE", len(relevant_jobs)),
        ("TOTAL REJECTED", len(rejected_jobs)),
        ("TOTAL NEW TELEGRAM", len(new_jobs)),
    ]

    for label, value in totals:
        print(f"{label:18} : {value}")

    print()
    print(
        "Reports created:"
    )

    for report in (
        OUTPUT_FILE,
        FULL_OUTPUT_FILE,
        REJECTED_OUTPUT_FILE,
        UNVERIFIED_OUTPUT_FILE,
        SOURCE_STATS_FILE,
        PROVIDER_HEALTH_FILE,
        RUN_SUMMARY_FILE,
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
    """Pick up to ``cap`` jobs spread evenly across every source.

    Without this, a cap truncates the largest providers first and the
    smaller (often more relevant) sources never get enriched at all.
    """
    from collections import defaultdict

    by_source = defaultdict(list)

    for job in unique_jobs:
        by_source[job.get("source") or "unknown"].append(job)

    sources = list(by_source)

    if not sources:
        return []

    cursor = {source: 0 for source in sources}

    selected = []
    count = 0

    while count < cap:
        progressed = False

        for source in sources:
            bucket = by_source[source]

            index = cursor[source]

            if index >= len(bucket):
                continue

            selected.append(bucket[index])
            cursor[source] = index + 1
            count += 1
            progressed = True

            if count >= cap:
                break

        if not progressed:
            break

    return selected


def _int_or_none(value):
    if not value:
        return None

    try:
        return int(value)
    except ValueError:
        return None


if __name__ == "__main__":
    main()