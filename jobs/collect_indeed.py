"""Broad multi-source job discovery using JobSpy."""

import json
from pathlib import Path

from jobspy import scrape_jobs

from profile import TARGET_ROLES, SKILLS, LOCATIONS


OUTPUT_DIR = Path("reports")
OUTPUT_FILE = OUTPUT_DIR / "indeed_jobs.json"


# ============================================================
# JOBSPY SOURCES
# ============================================================

JOBSPY_SITES = [
    "indeed",
    "linkedin",
    "glassdoor",
    "google",
    "zip_recruiter",
    "bayt",
    "naukri",
]


# ============================================================
# SETTINGS
# ============================================================

RESULTS_PER_QUERY = 30
HOURS_OLD = 48


# ============================================================
# SEARCH QUERIES
# ============================================================
#
# Discovery is intentionally broad.
#
# profile.py remains the source of truth for:
#   - target roles
#   - skills
#   - locations
#
# These queries simply make sure we don't depend on one
# giant Boolean query.
# ============================================================

SEARCH_QUERIES = [
    # Support
    "Application Support Engineer",
    "Production Support Engineer",
    "Technical Support Engineer",
    "Cloud Support Engineer",
    "Application Operations Engineer",
    "Production Operations Engineer",
    "Technical Operations Engineer",
    "Support Engineer",

    # Cloud / DevOps / SRE
    "Cloud Engineer",
    "Cloud Operations Engineer",
    "DevOps Engineer",
    "Junior DevOps Engineer",
    "Site Reliability Engineer",
    "SRE",
    "Platform Support Engineer",
    "Systems Support Engineer",
    "Production Engineer",

    # QA / Testing
    "QA Engineer",
    "Junior QA Engineer",
    "Quality Assurance Engineer",
    "Software QA Engineer",
    "Software Test Engineer",
    "Junior Test Engineer",
    "Test Engineer",
    "QA Analyst",
    "Junior QA Analyst",
    "Quality Analyst",
    "Quality Assurance Analyst",
    "Manual Tester",
    "Manual Testing Engineer",
    "Software Tester",
    "Application Tester",
    "QA Tester",
    "Functional Tester",
    "Functional Test Engineer",
    "Test Analyst",

    # Roles configured in profile.py
    *TARGET_ROLES,
]


# ============================================================
# LOCATIONS
# ============================================================

def build_locations():
    """
    Use ALL locations configured in profile.py.

    profile.py is the single source of truth.
    """

    locations = []

    for location in LOCATIONS:

        value = str(
            location
        ).strip()

        if not value:
            continue

        if value not in locations:

            locations.append(
                value
            )

    if not locations:

        locations.append(
            "Chennai"
        )

    return locations


# ============================================================
# QUERY CLEANUP
# ============================================================

def build_queries():
    """
    Build a clean unique query list.

    Keep profile roles and our broad discovery roles.
    """

    queries = []

    for query in SEARCH_QUERIES:

        value = str(
            query
        ).strip()

        if not value:
            continue

        if value not in queries:

            queries.append(
                value
            )

    return queries


# ============================================================
# JSON SAFETY
# ============================================================

def json_safe(value):
    """Convert JobSpy/Pandas values into JSON-safe values."""

    if value is None:
        return ""

    try:

        if value != value:
            return ""

    except Exception:
        pass

    if hasattr(
        value,
        "isoformat",
    ):

        try:

            return value.isoformat()

        except Exception:
            pass

    if isinstance(
        value,
        (list, tuple),
    ):

        return [
            json_safe(item)
            for item in value
        ]

    if isinstance(
        value,
        dict,
    ):

        return {
            str(key): json_safe(val)
            for key, val in value.items()
        }

    return str(value)


# ============================================================
# NORMALIZATION
# ============================================================

def normalize_job(job):
    """
    Preserve the complete JobSpy result.

    We keep all provider metadata so the downstream
    enrichment/matching pipeline can use it.
    """

    result = {}

    for column in job.index:

        key = str(
            column
        )

        try:

            value = job[column]

        except Exception:

            value = ""

        result[key] = json_safe(
            value
        )

    # --------------------------------------------------------
    # STANDARD FIELDS
    # --------------------------------------------------------

    result["source"] = (
        result.get("site")
        or result.get("source")
        or "jobspy"
    )

    result["title"] = (
        result.get("title")
        or ""
    )

    result["company"] = (
        result.get("company")
        or result.get("company_name")
        or ""
    )

    result["company_name"] = (
        result.get("company")
        or ""
    )

    result["location"] = (
        result.get("location")
        or ""
    )

    result["description"] = (
        result.get("description")
        or ""
    )

    result["url"] = (
        result.get("job_url")
        or result.get("url")
        or ""
    )

    result["job_url"] = (
        result.get("job_url")
        or result.get("url")
        or ""
    )

    result["date_posted"] = (
        result.get("date_posted")
        or result.get("posted_at")
        or ""
    )

    result["job_type"] = (
        result.get("job_type")
        or ""
    )

    result["employment_type"] = (
        result.get("employment_type")
        or result.get("job_type")
        or ""
    )

    result["is_remote"] = bool(
        result.get(
            "is_remote",
            False,
        )
    )

    result["source_job_id"] = (
        result.get("id")
        or ""
    )

    return result


# ============================================================
# NORMALIZED IDENTITY
# ============================================================

def normalize_url(url):
    """Normalize a URL for duplicate detection."""

    return (
        str(url or "")
        .strip()
        .lower()
        .rstrip("/")
    )


def normalize_text(value):
    """Normalize company/title text."""

    return (
        " ".join(
            str(value or "")
            .lower()
            .strip()
            .split()
        )
    )


def job_identity(job):
    """
    Stable identity across repeated searches.

    URL first.

    Company + title fallback.
    """

    url = normalize_url(
        job.get("url")
        or job.get("job_url")
    )

    if url:

        return (
            "url",
            url,
        )

    company = normalize_text(
        job.get("company")
        or job.get("company_name")
    )

    title = normalize_text(
        job.get("title")
    )

    if not company and not title:

        return None

    return (
        "job",
        company,
        title,
    )


# ============================================================
# DEDUPLICATION
# ============================================================

def remove_duplicates(jobs):
    """Deduplicate jobs across queries, locations and sources."""

    unique = []

    seen = set()

    for job in jobs:

        identity = job_identity(
            job
        )

        if identity is None:
            continue

        if identity in seen:
            continue

        seen.add(
            identity
        )

        unique.append(
            job
        )

    return unique


# ============================================================
# SINGLE SEARCH
# ============================================================

def collect_query(
    query,
    location,
):
    """
    Execute one independent JobSpy search.

    A failing source/query must never stop the other searches.
    """

    print(
        f"    Query: {query}"
    )

    try:

        google_search_term = (
            f"{query} "
            f"{location} India"
        )

        jobs = scrape_jobs(
            site_name=JOBSPY_SITES,
            search_term=query,
            google_search_term=google_search_term,
            location=location,
            results_wanted=RESULTS_PER_QUERY,
            hours_old=HOURS_OLD,
            country_indeed="India",
            verbose=1,
        )

    except Exception as error:

        print(
            f"    Query failed: {error}"
        )

        return []

    if jobs is None:

        print(
            "    No results."
        )

        return []

    results = []

    for _, job in jobs.iterrows():

        normalized = normalize_job(
            job
        )

        url = (
            normalized.get("url")
            or normalized.get("job_url")
            or ""
        )

        if not url:
            continue

        normalized[
            "search_query"
        ] = query

        normalized[
            "search_location"
        ] = location

        results.append(
            normalized
        )

    print(
        f"    Results: {len(results)}"
    )

    return results


# ============================================================
# MAIN
# ============================================================

def main():

    OUTPUT_DIR.mkdir(
        exist_ok=True
    )

    queries = build_queries()
    locations = build_locations()

    print()
    print("=" * 70)
    print("SIVA JOB AGENT — BROAD JOB DISCOVERY")
    print("=" * 70)

    print(
        "Sources:"
    )

    print(
        "  "
        + ", ".join(
            JOBSPY_SITES
        )
    )

    print()

    print(
        "Locations from profile.py:"
    )

    for location in locations:

        print(
            f"  ✓ {location}"
        )

    print()

    print(
        f"Search queries : {len(queries)}"
    )

    print(
        f"Locations      : {len(locations)}"
    )

    print(
        f"Searches       : "
        f"{len(queries) * len(locations)}"
    )

    print(
        f"Freshness      : {HOURS_OLD} hours"
    )

    print("=" * 70)

    all_jobs = []

    # --------------------------------------------------------
    # EVERY QUERY × EVERY PROFILE LOCATION
    # --------------------------------------------------------

    total_searches = (
        len(queries)
        * len(locations)
    )

    search_number = 0

    for location in locations:

        print()
        print(
            "=" * 70
        )

        print(
            f"LOCATION: {location}"
        )

        print(
            "=" * 70
        )

        for query in queries:

            search_number += 1

            print()
            print(
                f"[{search_number}/{total_searches}]"
            )

            results = collect_query(
                query,
                location,
            )

            all_jobs.extend(
                results
            )

    # --------------------------------------------------------
    # RAW TOTAL
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("DEDUPLICATION")
    print("=" * 70)

    print(
        f"Raw jobs collected : "
        f"{len(all_jobs)}"
    )

    unique_jobs = (
        remove_duplicates(
            all_jobs
        )
    )

    print(
        f"Unique jobs        : "
        f"{len(unique_jobs)}"
    )

    # --------------------------------------------------------
    # SOURCE COUNTS
    # --------------------------------------------------------

    source_counts = {}

    for job in unique_jobs:

        source = (
            job.get("source")
            or "unknown"
        )

        source_counts[
            source
        ] = (
            source_counts.get(
                source,
                0,
            )
            + 1
        )

    # --------------------------------------------------------
    # LOCATION COUNTS
    # --------------------------------------------------------

    location_counts = {}

    for job in unique_jobs:

        location = (
            job.get(
                "search_location"
            )
            or job.get(
                "location"
            )
            or "unknown"
        )

        location_counts[
            location
        ] = (
            location_counts.get(
                location,
                0,
            )
            + 1
        )

    # --------------------------------------------------------
    # SAVE
    # --------------------------------------------------------

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            unique_jobs,
            file,
            indent=2,
            ensure_ascii=False,
        )

    # --------------------------------------------------------
    # REPORT
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("JOBSPY COLLECTION RESULT")
    print("=" * 70)

    print(
        f"Raw jobs          : "
        f"{len(all_jobs)}"
    )

    print(
        f"Unique jobs       : "
        f"{len(unique_jobs)}"
    )

    print()

    print(
        "SOURCE BREAKDOWN"
    )

    for source, count in sorted(
        source_counts.items()
    ):

        print(
            f"{source:18} : {count}"
        )

    print()

    print(
        "LOCATION BREAKDOWN"
    )

    for location, count in sorted(
        location_counts.items()
    ):

        print(
            f"{location:18} : {count}"
        )

    print()

    print(
        f"Saved to: {OUTPUT_FILE}"
    )

    print()
    print("=" * 70)
    print("DISCOVERY COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
