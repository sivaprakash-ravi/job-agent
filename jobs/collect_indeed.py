import json
from pathlib import Path

from jobspy import scrape_jobs

from profile import TARGET_ROLES, SKILLS, LOCATIONS


OUTPUT_DIR = Path("reports")
OUTPUT_FILE = OUTPUT_DIR / "indeed_jobs.json"

JOBSPY_SITES = [
    "indeed",
    "linkedin",
    "glassdoor",
    "google",
    "zip_recruiter",
    "bayt",
    "naukri",
]

RESULTS_PER_SOURCE = 30
HOURS_OLD = 48


def build_search_term():
    roles = TARGET_ROLES
    skills = SKILLS

    role_terms = " OR ".join(
        f'"{role}"'
        for role in roles
    )

    skill_terms = " OR ".join(
        f'"{skill}"'
        for skill in skills
    )

    return (
        f"({role_terms}) "
        f"({skill_terms})"
    )


def build_location():
    return "Chennai"


def json_safe(value):
    if value is None:
        return ""

    try:
        if value != value:
            return ""
    except Exception:
        pass

    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            pass

    if isinstance(value, (list, tuple)):
        return [
            json_safe(item)
            for item in value
        ]

    if isinstance(value, dict):
        return {
            str(key): json_safe(val)
            for key, val in value.items()
        }

    return str(value)


def normalize_job(job):
    """
    Preserve the complete JobSpy row.

    This is important because experience can appear
    anywhere in the original listing data.
    """

    result = {}

    for column in job.index:
        key = str(column)

        try:
            value = job[column]
        except Exception:
            value = ""

        result[key] = json_safe(value)

    # Standard fields used by our matcher.
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


def remove_duplicate_urls(jobs):
    unique = []
    seen = set()

    for job in jobs:

        url = (
            job.get("url")
            or job.get("job_url")
            or ""
        ).strip()

        if not url:
            continue

        if url in seen:
            continue

        seen.add(url)
        unique.append(job)

    return unique


def main():

    OUTPUT_DIR.mkdir(
        exist_ok=True
    )

    search_term = build_search_term()
    location = build_location()

    print("=" * 70)
    print("JOBSPY DEEP JOB COLLECTION")
    print("=" * 70)
    print(
        f"Location : {location}"
    )
    print(
        f"Sources  : {', '.join(JOBSPY_SITES)}"
    )
    print(
        f"Freshness window : {HOURS_OLD} hours"
    )
    print()

    google_search_term = (
        " OR ".join(
            TARGET_ROLES[:15]
        )
        + f" jobs {location} India"
    )

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

    except Exception as error:

        print(
            "JobSpy search failed:"
            f" {error}"
        )

        jobs = None

    normalized_jobs = []

    if jobs is not None:

        for _, job in jobs.iterrows():

            normalized = normalize_job(
                job
            )

            if normalized.get(
                "url"
            ):

                normalized_jobs.append(
                    normalized
                )

    unique_jobs = (
        remove_duplicate_urls(
            normalized_jobs
        )
    )

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

    print()
    print("=" * 70)
    print("JOBSPY COLLECTION RESULT")
    print("=" * 70)
    print(
        f"Unique jobs: {len(unique_jobs)}"
    )

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
        f"Saved to: {OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()