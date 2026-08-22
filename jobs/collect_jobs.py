import json
import urllib.parse
import urllib.request
from pathlib import Path

from profile import TARGET_ROLES, SKILLS, LOCATIONS
from job_matcher import (
    keep_relevant_jobs,
    rank_jobs,
    get_rejected_jobs,
)


API_URL = "https://freehire.me/api/v1/jobs/search"

OUTPUT_DIR = Path("reports")

INDEED_FILE = OUTPUT_DIR / "indeed_jobs.json"

OUTPUT_FILE = OUTPUT_DIR / "jobs.json"

FULL_OUTPUT_FILE = OUTPUT_DIR / "all_ranked_jobs.json"

REJECTED_OUTPUT_FILE = (
    OUTPUT_DIR / "rejected_jobs.json"
)

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
        "posted_within_days": "3",
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
            "Indeed/JobSpy job report."
        )

        return []


def load_sent_jobs():
    if SENT_FILE.exists():

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

        except (
            json.JSONDecodeError,
            OSError,
        ):
            pass

    return set()


def save_sent_jobs(sent_jobs):

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


def save_json(
    filename,
    data,
):

    with open(
        filename,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            data,
            file,
            indent=2,
            ensure_ascii=False,
        )


def job_identity(job):

    url = (
        job.get("url")
        or job.get("job_url")
        or ""
    )

    if url:
        return url

    company = (
        job.get("company")
        or job.get("company_name")
        or ""
    )

    title = (
        job.get("title")
        or ""
    )

    return (
        f"{company}|{title}"
    ).lower().strip()


def main():

    OUTPUT_DIR.mkdir(
        exist_ok=True
    )

    # ---------------------------------------------------------
    # 1. Collect FreeHire jobs
    # ---------------------------------------------------------

    print("=" * 70)
    print("DAILY JOB AGENT")
    print("=" * 70)
    print()
    print("Collecting FreeHire jobs...")

    try:

        (
            freehire_jobs,
            meta,
        ) = collect_freehire_jobs()

    except Exception as error:

        print(
            "FreeHire collection failed:"
        )

        print(error)

        freehire_jobs = []
        meta = {}

    # ---------------------------------------------------------
    # 2. Load JobSpy jobs
    # ---------------------------------------------------------

    print(
        "Loading JobSpy jobs..."
    )

    indeed_jobs = load_indeed_jobs()

    # ---------------------------------------------------------
    # 3. Combine sources
    # ---------------------------------------------------------

    all_jobs = (
        freehire_jobs
        + indeed_jobs
    )

    print()
    print(
        f"FreeHire jobs returned : "
        f"{len(freehire_jobs)}"
    )

    print(
        f"JobSpy jobs returned   : "
        f"{len(indeed_jobs)}"
    )

    print(
        f"Combined raw jobs      : "
        f"{len(all_jobs)}"
    )

    print(
        f"FreeHire total matches : "
        f"{meta.get('total', 'unknown')}"
    )

    print()

    # ---------------------------------------------------------
    # 4. Remove duplicate URLs / identities
    # ---------------------------------------------------------

    unique_raw_jobs = []

    seen_jobs = set()

    for job in all_jobs:

        identity = job_identity(
            job
        )

        if not identity:
            continue

        if identity in seen_jobs:
            continue

        seen_jobs.add(
            identity
        )

        unique_raw_jobs.append(
            job
        )

    print(
        f"Unique raw jobs       : "
        f"{len(unique_raw_jobs)}"
    )

    # ---------------------------------------------------------
    # 5. Rank every job
    # ---------------------------------------------------------

    print(
        "Running strict job matcher..."
    )

    ranked_jobs = rank_jobs(
        unique_raw_jobs
    )

    # ---------------------------------------------------------
    # 6. Separate rejected jobs
    # ---------------------------------------------------------

    rejected_jobs = get_rejected_jobs(
        ranked_jobs
    )

    # ---------------------------------------------------------
    # 7. Keep only eligible jobs
    # ---------------------------------------------------------

    relevant_jobs = keep_relevant_jobs(
        ranked_jobs
    )

    # ---------------------------------------------------------
    # 8. Save ALL ranked jobs
    # ---------------------------------------------------------

    save_json(
        FULL_OUTPUT_FILE,
        ranked_jobs,
    )

    # ---------------------------------------------------------
    # 9. Save REJECTED jobs
    # ---------------------------------------------------------

    save_json(
        REJECTED_OUTPUT_FILE,
        rejected_jobs,
    )

    # ---------------------------------------------------------
    # 10. Remove previously sent jobs
    # ---------------------------------------------------------

    sent_jobs = load_sent_jobs()

    new_jobs = []

    for job in relevant_jobs:

        job_url = (
            job.get("url")
            or job.get("job_url")
            or ""
        )

        identity = (
            job_url
            or job_identity(job)
        )

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

    # ---------------------------------------------------------
    # 11. Save final Telegram jobs
    # ---------------------------------------------------------

    save_json(
        OUTPUT_FILE,
        new_jobs,
    )

    # ---------------------------------------------------------
    # 12. Print statistics
    # ---------------------------------------------------------

    print()
    print("=" * 70)
    print("MATCHING RESULTS")
    print("=" * 70)

    print(
        f"Raw unique jobs      : "
        f"{len(unique_raw_jobs)}"
    )

    print(
        f"Rejected jobs        : "
        f"{len(rejected_jobs)}"
    )

    print(
        f"Eligible jobs        : "
        f"{len(relevant_jobs)}"
    )

    print(
        f"New jobs to report   : "
        f"{len(new_jobs)}"
    )

    print(
        f"Previously seen      : "
        f"{len(relevant_jobs) - len(new_jobs)}"
    )

    print()

    # ---------------------------------------------------------
    # 13. Rejection statistics
    # ---------------------------------------------------------

    rejection_counts = {}

    for job in rejected_jobs:

        details = job.get(
            "match_details",
            {},
        )

        reasons = details.get(
            "filter_reasons",
            [],
        )

        for reason in reasons:

            rejection_counts[
                reason
            ] = (
                rejection_counts.get(
                    reason,
                    0,
                )
                + 1
            )

    print(
        "REJECTION REASONS"
    )

    if rejection_counts:

        for reason, count in sorted(
            rejection_counts.items(),
            key=lambda item: item[1],
            reverse=True,
        ):

            print(
                f"{count:5} : {reason}"
            )

    else:

        print(
            "No rejection reasons recorded."
        )

    print()

    # ---------------------------------------------------------
    # 14. Print final jobs
    # ---------------------------------------------------------

    print(
        "NEW ELIGIBLE JOBS"
    )

    for index, job in enumerate(
        new_jobs[:20],
        start=1,
    ):

        title = job.get(
            "title",
            "Unknown title",
        )

        company = (
            job.get("company")
            or job.get(
                "company_name",
                "Unknown company",
            )
        )

        location = job.get(
            "location",
            "Unknown location",
        )

        job_url = (
            job.get("url")
            or job.get(
                "job_url",
                "",
            )
        )

        source = job.get(
            "source",
            "Unknown",
        )

        print(
            f"{index}. "
            f"{title} — "
            f"{job.get('match_score', 0)}% "
            f"({job.get('match_category', 'Match')})"
        )

        print(
            f"   Source   : {source}"
        )

        print(
            f"   Company  : {company}"
        )

        print(
            f"   Location : {location}"
        )

        print(
            f"   URL      : {job_url}"
        )

        print()

    # ---------------------------------------------------------
    # 15. Output files
    # ---------------------------------------------------------

    print(
        f"Saved final jobs to : "
        f"{OUTPUT_FILE}"
    )

    print(
        f"Saved ranked jobs to: "
        f"{FULL_OUTPUT_FILE}"
    )

    print(
        f"Saved rejected jobs : "
        f"{REJECTED_OUTPUT_FILE}"
    )

    print(
        f"Saved history to    : "
        f"{SENT_FILE}"
    )


if __name__ == "__main__":
    main()