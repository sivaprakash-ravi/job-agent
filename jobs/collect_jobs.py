import json
import urllib.parse
import urllib.request
from pathlib import Path

from profile import TARGET_ROLES, SKILLS
from job_matcher import keep_relevant_jobs, rank_jobs


API_URL = "https://freehire.me/api/v1/jobs/search"

OUTPUT_DIR = Path("reports")
INDEED_FILE = OUTPUT_DIR / "indeed_jobs.json"
OUTPUT_FILE = OUTPUT_DIR / "jobs.json"
FULL_OUTPUT_FILE = OUTPUT_DIR / "all_ranked_jobs.json"
SENT_FILE = OUTPUT_DIR / "sent_jobs.json"


def collect_freehire_jobs():
    search_terms = TARGET_ROLES + SKILLS

    params = {
        "q": " ".join(search_terms),
        "countries": "IN",
        "category": (
            "devops,sre,support,"
            "operations,software_engineering,"
            "qa,testing"
        ),
        "seniority": "junior,middle",
        "employment_type": "full_time",
        "posted_within_days": "7",
        "sort": "posted_at",
        "order": "desc",
        "limit": "100",
        "offset": "0",
    }

    url = (
        API_URL
        + "?"
        + urllib.parse.urlencode(params)
    )

    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "job-agent/1.0",
        },
    )

    with urllib.request.urlopen(
        request,
        timeout=30,
    ) as response:

        data = json.loads(
            response.read().decode(
                "utf-8"
            )
        )

    return (
        data.get("data", []),
        data.get("meta", {}),
    )


def load_indeed_jobs():
    if not INDEED_FILE.exists():
        return []

    try:

        with open(
            INDEED_FILE,
            "r",
            encoding="utf-8",
        ) as file:

            jobs = json.load(file)

        if not isinstance(
            jobs,
            list,
        ):
            return []

        return jobs

    except (
        json.JSONDecodeError,
        OSError,
    ):

        print(
            "Warning: Could not read "
            "JobSpy job report."
        )

        return []


def load_sent_jobs():
    if not SENT_FILE.exists():
        return set()

    try:

        with open(
            SENT_FILE,
            "r",
            encoding="utf-8",
        ) as file:

            data = json.load(file)

        if not isinstance(
            data,
            list,
        ):
            return set()

        return set(data)

    except (
        json.JSONDecodeError,
        OSError,
    ):

        print(
            "Warning: Could not read "
            "sent job history."
        )

        return set()


def save_sent_jobs(sent_jobs):
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


def job_identity(job):
    """
    Create a stable identity for a job.

    URL is preferred because it is the strongest
    identifier across repeated workflow runs.
    """

    url = (
        job.get("url")
        or job.get("job_url")
        or ""
    )

    if url:
        return url.strip()

    company = (
        job.get("company")
        or job.get("company_name")
        or ""
    )

    title = (
        job.get("title")
        or ""
    )

    location = (
        job.get("location")
        or ""
    )

    return "|".join(
        [
            str(company).strip().lower(),
            str(title).strip().lower(),
            str(location).strip().lower(),
        ]
    )


def remove_duplicate_urls(jobs):
    """Remove duplicate raw jobs by URL."""

    unique_jobs = []
    seen = set()

    for job in jobs:

        identity = job_identity(
            job
        )

        if not identity:
            continue

        if identity in seen:
            continue

        seen.add(identity)
        unique_jobs.append(job)

    return unique_jobs


def main():

    OUTPUT_DIR.mkdir(
        exist_ok=True
    )

    # ---------------------------------------------------------
    # 1. Collect FreeHire.
    # ---------------------------------------------------------

    try:

        freehire_jobs, meta = (
            collect_freehire_jobs()
        )

    except Exception as error:

        print(
            "FreeHire search failed:"
            f" {error}"
        )

        freehire_jobs = []
        meta = {}

    # ---------------------------------------------------------
    # 2. Load JobSpy results.
    # ---------------------------------------------------------

    indeed_jobs = (
        load_indeed_jobs()
    )

    # ---------------------------------------------------------
    # 3. Combine.
    # ---------------------------------------------------------

    all_jobs = (
        freehire_jobs
        + indeed_jobs
    )

    all_jobs = (
        remove_duplicate_urls(
            all_jobs
        )
    )

    print("=" * 70)
    print("JOB AGENT MATCHING PIPELINE")
    print("=" * 70)
    print(
        "FreeHire jobs returned : "
        f"{len(freehire_jobs)}"
    )
    print(
        "JobSpy jobs returned   : "
        f"{len(indeed_jobs)}"
    )
    print(
        "Unique raw jobs        : "
        f"{len(all_jobs)}"
    )
    print(
        "FreeHire total matches : "
        f"{meta.get('total', 'unknown')}"
    )
    print()

    # ---------------------------------------------------------
    # 4. Rank every raw job.
    # ---------------------------------------------------------

    ranked_jobs = rank_jobs(
        all_jobs
    )

    # ---------------------------------------------------------
    # 5. Keep only jobs that pass ALL hard filters.
    # ---------------------------------------------------------

    relevant_jobs = (
        keep_relevant_jobs(
            ranked_jobs
        )
    )

    # ---------------------------------------------------------
    # 6. Remove jobs already successfully sent
    #    in previous runs.
    #
    # IMPORTANT:
    # We DO NOT modify sent_jobs.json here.
    # Telegram must succeed first.
    # ---------------------------------------------------------

    sent_jobs = (
        load_sent_jobs()
    )

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

    # ---------------------------------------------------------
    # 7. Save Telegram report.
    # ---------------------------------------------------------

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            new_jobs,
            file,
            indent=2,
            ensure_ascii=False,
        )

    # ---------------------------------------------------------
    # 8. Save complete ranked report.
    # ---------------------------------------------------------

    with open(
        FULL_OUTPUT_FILE,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            ranked_jobs,
            file,
            indent=2,
            ensure_ascii=False,
        )

    # ---------------------------------------------------------
    # 9. Print results.
    # ---------------------------------------------------------

    ignored_count = (
        len(all_jobs)
        - len(relevant_jobs)
    )

    already_seen_count = (
        len(relevant_jobs)
        - len(new_jobs)
    )

    print(
        f"Jobs after hard filtering : "
        f"{len(relevant_jobs)}"
    )

    print(
        f"New jobs to report        : "
        f"{len(new_jobs)}"
    )

    print(
        f"Already sent previously   : "
        f"{already_seen_count}"
    )

    print(
        f"Filtered/ignored          : "
        f"{ignored_count}"
    )

    print()

    for index, job in enumerate(
        new_jobs[:30],
        start=1,
    ):

        title = (
            job.get("title")
            or "Unknown title"
        )

        company = (
            job.get("company")
            or job.get(
                "company_name"
            )
            or "Unknown company"
        )

        location = (
            job.get("location")
            or "Unknown location"
        )

        source = (
            job.get("source")
            or "Unknown source"
        )

        url = (
            job.get("url")
            or job.get("job_url")
            or ""
        )

        print(
            f"{index}. "
            f"{title} — "
            f"{job.get('match_score', 0)}%"
        )

        print(
            f"   Company  : {company}"
        )

        print(
            f"   Location : {location}"
        )

        print(
            f"   Source   : {source}"
        )

        print(
            f"   URL      : {url}"
        )

        print()

    print(
        f"Saved final jobs to : "
        f"{OUTPUT_FILE}"
    )

    print(
        f"Saved ranked jobs to: "
        f"{FULL_OUTPUT_FILE}"
    )

    print(
        "Sent history will be updated "
        "ONLY after Telegram succeeds."
    )


if __name__ == "__main__":
    main()