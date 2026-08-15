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

RESULTS_PER_SOURCE = 20
HOURS_OLD = 72


def build_search_term():
    roles = TARGET_ROLES[:8]
    skills = SKILLS[:8]

    role_terms = " OR ".join(f'"{role}"' for role in roles)
    skill_terms = " OR ".join(f'"{skill}"' for skill in skills)

    return f"({role_terms}) ({skill_terms})"


def build_location():
    if LOCATIONS:
        return LOCATIONS[0]

    return "Bangalore"


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
        "source": normalize_value(job.get("site")) or "jobspy",
        "title": normalize_value(job.get("title")),
        "company": normalize_value(job.get("company")),
        "company_name": normalize_value(job.get("company")),
        "location": normalize_value(job.get("location")),
        "description": normalize_value(job.get("description")),
        "url": normalize_value(job.get("job_url")),
        "job_url": normalize_value(job.get("job_url")),
        "job_type": normalize_value(job.get("job_type")),
        "date_posted": normalize_value(job.get("date_posted")),
        "is_remote": bool(job.get("is_remote", False)),
        "source_job_id": normalize_value(job.get("id")),
    }


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)

    search_term = build_search_term()
    location = build_location()

    print("=" * 70)
    print("JOBSPY MULTI-SOURCE JOB SEARCH")
    print("=" * 70)
    print(f"Search location : {location}")
    print(f"Sources         : {', '.join(JOBSPY_SITES)}")
    print(f"Hours old       : {HOURS_OLD}")
    print()

    google_search_term = (
        f"{' '.join(TARGET_ROLES[:5])} jobs "
        f"{location} India since yesterday"
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
        print(f"JobSpy search failed: {error}")
        print("Saving an empty JobSpy report.")
        jobs = None

    normalized_jobs = []

    if jobs is not None:
        for _, job in jobs.iterrows():
            normalized_jobs.append(normalize_job(job))

    # Remove entries without a usable URL.
    normalized_jobs = [
        job for job in normalized_jobs
        if job.get("url")
    ]

    # Remove duplicate URLs returned across searches/providers.
    unique_jobs = []
    seen_urls = set()

    for job in normalized_jobs:
        url = job["url"]

        if url not in seen_urls:
            seen_urls.add(url)
            unique_jobs.append(job)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
        json.dump(
            unique_jobs,
            file,
            indent=2,
            ensure_ascii=False,
        )

    print()
    print("=" * 70)
    print("JOBSPY RESULTS")
    print("=" * 70)
    print(f"Total unique jobs: {len(unique_jobs)}")
    print()

    source_counts = {}

    for job in unique_jobs:
        source = job.get("source", "unknown")
        source_counts[source] = source_counts.get(source, 0) + 1

    for source, count in sorted(source_counts.items()):
        print(f"{source:15} : {count}")

    print()
    print(f"Saved to: {OUTPUT_FILE}")
    print()

    for index, job in enumerate(unique_jobs[:30], start=1):
        print(
            f"{index}. "
            f"{job.get('title', 'Unknown title')} | "
            f"{job.get('company', 'Unknown company')} | "
            f"{job.get('source', 'unknown')}"
        )


if __name__ == "__main__":
    main()
