import json
from pathlib import Path

from jobspy import scrape_jobs

from profile import TARGET_ROLES, SKILLS, LOCATIONS


OUTPUT_DIR = Path("reports")
OUTPUT_FILE = OUTPUT_DIR / "indeed_jobs.json"


# JobSpy-supported sources currently being used.
JOBSPY_SITES = [
    "indeed",
    "linkedin",
    "glassdoor",
    "google",
    "zip_recruiter",
    "bayt",
    "naukri",
]


# Number of results requested per search.
RESULTS_PER_SOURCE = 100

# Search jobs posted within the last 72 hours.
HOURS_OLD = 72


def build_search_terms():
    """
    Build multiple focused searches so every role family
    gets a chance to appear.

    We intentionally do not use only the first few roles.
    """

    support_roles = [
        role
        for role in TARGET_ROLES
        if any(
            keyword in role.lower()
            for keyword in (
                "support",
                "operations",
            )
        )
    ]

    cloud_devops_roles = [
        role
        for role in TARGET_ROLES
        if any(
            keyword in role.lower()
            for keyword in (
                "cloud",
                "devops",
                "site reliability",
                "sre",
            )
        )
    ]

    qa_roles = [
        role
        for role in TARGET_ROLES
        if any(
            keyword in role.lower()
            for keyword in (
                "qa",
                "quality",
                "test",
                "tester",
            )
        )
    ]

    searches = []

    if support_roles:
        searches.append(
            " OR ".join(
                f'"{role}"'
                for role in support_roles
            )
        )

    if cloud_devops_roles:
        searches.append(
            " OR ".join(
                f'"{role}"'
                for role in cloud_devops_roles
            )
        )

    if qa_roles:
        searches.append(
            " OR ".join(
                f'"{role}"'
                for role in qa_roles
            )
        )

    # Fallback if role categorisation ever produces nothing.
    if not searches:
        searches.append(
            " OR ".join(
                f'"{role}"'
                for role in TARGET_ROLES
            )
        )

    return searches


def build_location_searches():
    """
    Search each preferred location separately.

    This prevents LOCATIONS[0] from limiting the entire
    search to Chennai.
    """

    if LOCATIONS:
        return LOCATIONS

    return ["Bangalore"]


def build_google_search_term(
    roles,
    location,
):
    """
    Build a Google Jobs query for the current role family
    and location.
    """

    role_text = " ".join(
        roles[:10]
    )

    return (
        f"{role_text} jobs "
        f"{location} India "
        "since yesterday"
    )


def normalize_value(value):
    if value is None:
        return ""

    try:
        if value != value:
            return ""
    except Exception:
        pass

    return str(value)


def normalize_job(job):
    return {
        "source": (
            normalize_value(
                job.get("site")
            )
            or "jobspy"
        ),
        "title": normalize_value(
            job.get("title")
        ),
        "company": normalize_value(
            job.get("company")
        ),
        "company_name": normalize_value(
            job.get("company")
        ),
        "location": normalize_value(
            job.get("location")
        ),
        "description": normalize_value(
            job.get("description")
        ),
        "url": normalize_value(
            job.get("job_url")
        ),
        "job_url": normalize_value(
            job.get("job_url")
        ),
        "job_type": normalize_value(
            job.get("job_type")
        ),
        "date_posted": normalize_value(
            job.get("date_posted")
        ),
        "is_remote": bool(
            job.get(
                "is_remote",
                False,
            )
        ),
        "source_job_id": normalize_value(
            job.get("id")
        ),
    }


def run_jobspy_search(
    search_term,
    google_search_term,
    location,
):
    """
    Run one JobSpy search.

    Errors from one search should not stop all other
    locations/role families.
    """

    print("-" * 70)
    print(f"Location : {location}")
    print(f"Search   : {search_term}")
    print()

    try:
        jobs = scrape_jobs(
            site_name=JOBSPY_SITES,
            search_term=search_term,
            google_search_term=google_search_term,
            location=location,
            results_wanted=RESULTS_PER_SOURCE,
            hours_old=HOURS_OLD,
            country_indeed="India",
            verbose=1,
        )

        if jobs is None:
            return []

        normalized_jobs = []

        for _, job in jobs.iterrows():
            normalized_jobs.append(
                normalize_job(job)
            )

        return normalized_jobs

    except Exception as error:
        print(
            f"JobSpy search failed for "
            f"{location}: {error}"
        )
        return []


def deduplicate_jobs(jobs):
    """
    Remove duplicate listings.

    URL is the strongest identifier.

    If a source returns different URLs for the same
    company + title, we also remove that duplicate.
    """

    unique_jobs = []

    seen_urls = set()
    seen_company_roles = set()

    for job in jobs:
        url = job.get("url", "").strip()

        company = (
            job.get("company")
            or job.get("company_name")
            or ""
        ).strip().lower()

        title = (
            job.get("title")
            or ""
        ).strip().lower()

        company_role_key = (
            company,
            title,
        )

        # Prefer URL when available.
        if url:
            if url in seen_urls:
                continue

            seen_urls.add(url)

        # Strict company + designation deduplication.
        if company_role_key in seen_company_roles:
            continue

        seen_company_roles.add(
            company_role_key
        )

        unique_jobs.append(job)

    return unique_jobs


def main():
    OUTPUT_DIR.mkdir(
        exist_ok=True
    )

    searches = build_search_terms()
    locations = build_location_searches()

    print("=" * 70)
    print("JOBSPY MULTI-SOURCE JOB SEARCH")
    print("=" * 70)
    print(
        f"Locations       : "
        f"{', '.join(locations)}"
    )
    print(
        f"Sources         : "
        f"{', '.join(JOBSPY_SITES)}"
    )
    print(
        f"Role searches   : "
        f"{len(searches)}"
    )
    print(
        f"Hours old       : "
        f"{HOURS_OLD}"
    )
    print()

    all_jobs = []

    # ---------------------------------------------------------
    # Search every role family across every preferred location.
    # ---------------------------------------------------------

    for search_term in searches:
        for location in locations:

            google_search_term = (
                build_google_search_term(
                    TARGET_ROLES,
                    location,
                )
            )

            jobs = run_jobspy_search(
                search_term=search_term,
                google_search_term=(
                    google_search_term
                ),
                location=location,
            )

            all_jobs.extend(jobs)

    # ---------------------------------------------------------
    # Keep jobs with usable URLs.
    # ---------------------------------------------------------

    all_jobs = [
        job
        for job in all_jobs
        if job.get("url")
    ]

    # ---------------------------------------------------------
    # Strict source/result deduplication.
    # ---------------------------------------------------------

    unique_jobs = deduplicate_jobs(
        all_jobs
    )

    # ---------------------------------------------------------
    # Save normalized JobSpy results.
    # ---------------------------------------------------------

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

    # ---------------------------------------------------------
    # Print summary.
    # ---------------------------------------------------------

    print()
    print("=" * 70)
    print("JOBSPY RESULTS")
    print("=" * 70)

    print(
        f"Raw collected jobs : "
        f"{len(all_jobs)}"
    )

    print(
        f"Total unique jobs  : "
        f"{len(unique_jobs)}"
    )

    print()

    source_counts = {}

    for job in unique_jobs:
        source = (
            job.get("source")
            or "unknown"
        )

        source_counts[source] = (
            source_counts.get(
                source,
                0,
            )
            + 1
        )

    for source, count in sorted(
        source_counts.items()
    ):
        print(
            f"{source:15} : {count}"
        )

    print()
    print(
        f"Saved to: "
        f"{OUTPUT_FILE}"
    )
    print()

    for index, job in enumerate(
        unique_jobs[:30],
        start=1,
    ):
        print(
            f"{index}. "
            f"{job.get('title', 'Unknown title')} | "
            f"{job.get('company', 'Unknown company')} | "
            f"{job.get('source', 'unknown')} | "
            f"{job.get('location', 'Unknown location')}"
        )


if __name__ == "__main__":
    main()