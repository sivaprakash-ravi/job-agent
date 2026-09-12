"""Run every configured source adapter concurrently.

Each adapter runs independently:

- a failure in one provider never stops the others
- every provider returns {provider, status, count, error, jobs}
- multi-board adapters (JobSpy) are expanded into per-site results
- results are aggregated into reports/source_stats.json

Status values: ok, blocked, unavailable, error.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed

from canonical import deduplicate_jobs

from sources import (
    ashby_source,
    flexjobs_source,
    foundit_source,
    freehire_source,
    greenhouse_source,
    himalayas_source,
    india_boards_source,
    jobspy_source,
    lever_source,
    naukri_source,
    remoteco_source,
    remoteok_source,
    timesjobs_source,
    wellfound_source,
    weworkremotely_source,
    workingnomads_source,
    yc_source,
)

from sources.base import build_locations, build_search_queries


JOBSPY_SITE_LABELS = {
    "linkedin": "LinkedIn",
    "indeed": "Indeed",
    "glassdoor": "Glassdoor",
    "google": "Google",
    "zip_recruiter": "ZipRecruiter",
    "bayt": "Bayt",
    "naukri": "Naukri",
}

SINGLE_PROVIDERS = [
    ("Naukri", naukri_source, "naukri"),
    ("Foundit", foundit_source, "foundit"),
    ("Wellfound", wellfound_source, "wellfound"),
    ("YC", yc_source, "yc"),
    ("Himalayas", himalayas_source, "himalayas"),
    ("Remote OK", remoteok_source, "remoteok"),
    ("WWR", weworkremotely_source, "weworkremotely"),
    ("Remote.co", remoteco_source, "remoteco"),
    ("Working Nomads", workingnomads_source, "workingnomads"),
    ("FlexJobs", flexjobs_source, "flexjobs"),
    ("TimesJobs", timesjobs_source, "timesjobs"),
    ("Instahyre", india_boards_source, "instahyre"),
    ("Cutshort", india_boards_source, "cutshort"),
    ("Unstop", india_boards_source, "unstop"),
    ("Shine", india_boards_source, "shine"),
    ("Freshersworld", india_boards_source, "freshersworld"),
    ("FreeHire", freehire_source, "freehire"),
    ("Greenhouse", greenhouse_source, "greenhouse"),
    ("Lever", lever_source, "lever"),
    ("Ashby", ashby_source, "ashby"),
]

MULTI_PROVIDERS = [
    ("JobSpy", jobspy_source, "jobspy"),
]


def _build_single_runners():
    runners = []

    for label, module, runner_key in SINGLE_PROVIDERS:
        runner = getattr(module, f"run_{runner_key}", None)

        if runner is None:
            runner = module.run

        def call(search_queries, locations, _runner=runner):
            return _runner(search_queries, locations)

        runners.append((label, call))

    return runners


def _build_multi_runners():
    runners = []

    for label, module, runner_key in MULTI_PROVIDERS:
        runner = module.run

        def call(search_queries, locations, _runner=runner):
            return _runner(search_queries, locations)

        runners.append((label, call))

    return runners


SINGLE_RUNNERS = _build_single_runners()
MULTI_RUNNERS = _build_multi_runners()


def split_jobspy_result(label, result):
    """Expand a JobSpy result into one entry per site."""
    if not result.get("jobs"):
        error = result.get("error") or result.get("status")

        return [
            {
                "provider": label,
                "status": result.get("status", "error"),
                "count": 0,
                "error": error or "no results",
                "jobs": [],
            }
        ]

    buckets = {}

    for job in result.get("jobs"):
        source = str(job.get("source") or "unknown")

        buckets.setdefault(source, []).append(job)

    entries = []

    for source, jobs in sorted(buckets.items()):
        display = JOBSPY_SITE_LABELS.get(
            source,
            source.capitalize(),
        )

        entries.append(
            {
                "provider": display,
                "status": result.get("status", "ok"),
                "count": len(jobs),
                "error": "",
                "jobs": jobs,
            }
        )

    return entries


def run_sources(search_queries=None, locations=None, max_workers=12):
    """Run all providers and return (results, unique_jobs, stats)."""
    if search_queries is None:
        search_queries = build_search_queries()

    if locations is None:
        locations = build_locations()

    results = []

    tasks = [
        (label, runner, False)
        for label, runner in SINGLE_RUNNERS
    ]

    tasks += [
        (label, runner, True)
        for label, runner in MULTI_RUNNERS
    ]

    with ThreadPoolExecutor(
        max_workers=max_workers,
    ) as executor:

        future_map = {
            executor.submit(
                runner,
                search_queries,
                locations,
            ): (label, is_multi)
            for label, runner, is_multi in tasks
        }

        for future in as_completed(future_map):

            label, is_multi = future_map[future]

            try:
                result = future.result()
            except Exception as error:
                result = {
                    "provider": label,
                    "status": "error",
                    "count": 0,
                    "error": str(error),
                    "jobs": [],
                }

            if result is None:
                result = {
                    "provider": label,
                    "status": "error",
                    "count": 0,
                    "error": "Provider returned no result",
                    "jobs": [],
                }

            if is_multi:
                results.extend(split_jobspy_result(label, result))
            else:
                results.append(result)

    results.sort(
        key=lambda result: (
            result.get("count", 0),
            str(result.get("provider", "")),
        ),
        reverse=True,
    )

    stats, all_jobs = build_stats(results)

    unique_jobs = deduplicate_jobs(all_jobs)

    return results, unique_jobs, stats


def build_stats(results):
    """Aggregate provider stats and the full raw discovery set."""
    provider_stats = []
    all_jobs = []

    for result in results:
        provider = result.get("provider", "unknown")
        jobs = result.get("jobs") or []
        count = len(jobs)

        provider_stats.append(
            {
                "provider": provider,
                "status": result.get("status", "error"),
                "count": count,
                "error": result.get("error", ""),
            }
        )

        all_jobs.extend(jobs)

    stats = {
        "providers": provider_stats,
        "summary": {
            "total_discovered": len(all_jobs),
        },
    }

    return stats, all_jobs


def print_source_breakdown(results, unique_jobs, total_jobs):
    """Print the SOURCE BREAKDOWN block."""
    print()
    print("=" * 70)
    print("SOURCE BREAKDOWN")
    print("=" * 70)

    ordered = [
        "LinkedIn",
        "Indeed",
        "Naukri",
        "Foundit",
        "Wellfound",
        "YC",
        "Himalayas",
        "Remote OK",
        "WWR",
        "Remote.co",
        "Working Nomads",
        "TimesJobs",
        "Shine",
        "Freshersworld",
        "Instahyre",
        "Cutshort",
        "Unstop",
        "FreeHire",
        "Greenhouse",
        "Lever",
        "Ashby",
        "Glassdoor",
        "ZipRecruiter",
        "Bayt",
    ]

    result_by_provider = {
        str(result.get("provider")): result
        for result in results
    }

    source_counts = {}

    for job in total_jobs:
        source = str(job.get("source") or "unknown")
        source_counts[source] = source_counts.get(source, 0) + 1

    display_names = list(ordered) + [
        provider
        for provider in result_by_provider
        if provider not in ordered
    ]

    printed = set()

    for provider in display_names:
        if provider in printed:
            continue

        printed.add(provider)

        result = result_by_provider.get(provider)

        if not result:
            continue

        count = source_counts.get(
            str(provider).lower(),
            0,
        )

        status = result.get("status", "?")
        error = result.get("error", "")

        print(f"{provider:18} : {count}  [{status}]")

        if error:
            print(f"                   - {error[:110]}")

    print("-" * 70)
    print("TOTAL DISCOVERED".ljust(20) + f": {len(total_jobs)}")
    print("TOTAL UNIQUE".ljust(20) + f": {len(unique_jobs)}")