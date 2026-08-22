import json
from pathlib import Path

from profile import TARGET_ROLES, SKILLS, LOCATIONS
from job_matcher import keep_relevant_jobs, rank_jobs


API_URL = "https://freehire.me/api/v1/jobs/search"

OUTPUT_DIR = Path("reports")

INDEED_FILE = OUTPUT_DIR / "indeed_jobs.json"
OUTPUT_FILE = OUTPUT_DIR / "jobs.json"
FULL_OUTPUT_FILE = OUTPUT_DIR / "all_ranked_jobs.json"

REJECTED_FILE = OUTPUT_DIR / "rejected_jobs.json"
REJECTION_SUMMARY_FILE = OUTPUT_DIR / "rejection_summary.json"

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

    import urllib.parse
    import urllib.request

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
            "JobSpy report."
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

                return set(
                    json.load(file)
                )

        except (
            json.JSONDecodeError,
            OSError,
        ):

            pass

    return set()


def save_sent_jobs(
    sent_jobs
):

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
    path,
    data,
):

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


def build_rejection_report(
    ranked_jobs
):
    """
    Create a detailed report containing
    every rejected job and the exact reasons.
    """

    rejected = []

    summary = {}

    for job in ranked_jobs:

        category = job.get(
            "match_category",
            "",
        )

        if category != "Ignore":
            continue

        details = job.get(
            "match_details",
            {},
        )

        reasons = details.get(
            "filter_reasons",
            [],
        )

        if not reasons:

            reasons = [
                "Rejected by matcher"
            ]

        # Count each rejection reason.
        for reason in reasons:

            summary[reason] = (
                summary.get(
                    reason,
                    0,
                )
                + 1
            )

        rejected.append(
            {
                "title": job.get(
                    "title",
                    "Unknown title",
                ),
                "company": job.get(
                    "company"
                    or job.get(
                        "company_name",
                        "Unknown company",
                    )
                ),
                "location": job.get(
                    "location",
                    "Unknown location",
                ),
                "source": job.get(
                    "source",
                    "Unknown source",
                ),
                "url": (
                    job.get("url")
                    or job.get(
                        "job_url",
                        "",
                    )
                ),
                "match_score": job.get(
                    "match_score",
                    0,
                ),
                "reasons": reasons,
                "experience_analysis": (
                    details.get(
                        "experience_analysis",
                        {},
                    )
                ),
            }
        )

    # Sort most common reasons first.
    summary = dict(
        sorted(
            summary.items(),
            key=lambda item: item[1],
            reverse=True,
        )
    )

    return rejected, summary


def main():

    OUTPUT_DIR.mkdir(
        exist_ok=True
    )

    # ========================================================
    # 1. Collect FreeHire
    # ========================================================

    try:

        freehire_jobs, meta = (
            collect_freehire_jobs()
        )

    except Exception as error:

        print(
            "FreeHire collection failed:"
            f" {error}"
        )

        freehire_jobs = []
        meta = {}

    # ========================================================
    # 2. Load JobSpy
    # ========================================================

    indeed_jobs = (
        load_indeed_jobs()
    )

    # ========================================================
    # 3. Combine
    # ========================================================

    all_jobs = (
        freehire_jobs
        + indeed_jobs
    )

    print()
    print("=" * 70)
    print("DAILY JOB AGENT — DEEP FILTER")
    print("=" * 70)

    print(
        "FreeHire jobs :",
        len(freehire_jobs),
    )

    print(
        "JobSpy jobs   :",
        len(indeed_jobs),
    )

    print(
        "Raw combined  :",
        len(all_jobs),
    )

    print(
        "FreeHire total:",
        meta.get(
            "total",
            "unknown",
        ),
    )

    print()

    # ========================================================
    # 4. Deep ranking
    # ========================================================

    ranked_jobs = rank_jobs(
        all_jobs
    )

    # ========================================================
    # 5. Save rejection information
    # ========================================================

    rejected_jobs, rejection_summary = (
        build_rejection_report(
            ranked_jobs
        )
    )

    save_json(
        REJECTED_FILE,
        rejected_jobs,
    )

    save_json(
        REJECTION_SUMMARY_FILE,
        rejection_summary,
    )

    # ========================================================
    # 6. Keep only valid jobs
    # ========================================================

    relevant_jobs = (
        keep_relevant_jobs(
            ranked_jobs
        )
    )

    # ========================================================
    # 7. Remove previously sent jobs
    # ========================================================

    sent_jobs = (
        load_sent_jobs()
    )

    new_jobs = []

    for job in relevant_jobs:

        job_url = (
            job.get("url")
            or job.get("job_url")
            or ""
        )

        if (
            job_url
            and job_url not in sent_jobs
        ):

            new_jobs.append(
                job
            )

    # IMPORTANT:
    # Do NOT mark jobs as sent here.
    #
    # Telegram must succeed first.
    #
    # Your existing Telegram workflow should
    # handle the successful-send history.

    # ========================================================
    # 8. Save Telegram report
    # ========================================================

    save_json(
        OUTPUT_FILE,
        new_jobs,
    )

    # ========================================================
    # 9. Save complete ranking
    # ========================================================

    save_json(
        FULL_OUTPUT_FILE,
        ranked_jobs,
    )

    # ========================================================
    # 10. Console summary
    # ========================================================

    print()
    print("=" * 70)
    print("FILTER RESULT")
    print("=" * 70)

    print(
        "Total ranked jobs :",
        len(ranked_jobs),
    )

    print(
        "Rejected jobs     :",
        len(rejected_jobs),
    )

    print(
        "Eligible jobs     :",
        len(relevant_jobs),
    )

    print(
        "New jobs          :",
        len(new_jobs),
    )

    print()

    print(
        "Rejected report:",
        REJECTED_FILE,
    )

    print(
        "Rejection summary:",
        REJECTION_SUMMARY_FILE,
    )

    print()

    print(
        "Top rejection reasons:"
    )

    for reason, count in list(
        rejection_summary.items()
    )[:15]:

        print(
            f"  {count:4} × {reason}"
        )

    print()

    # ========================================================
    # 11. Show accepted jobs
    # ========================================================

    print(
        "Eligible jobs:"
    )

    for index, job in enumerate(
        new_jobs[:20],
        start=1,
    ):

        print(
            f"{index}. "
            f"{job.get('title', 'Unknown')} "
            f"| "
            f"{job.get('company', 'Unknown')} "
            f"| "
            f"{job.get('source', 'Unknown')} "
            f"| "
            f"{job.get('match_score', 0)}%"
        )

    print()
    print(
        "Saved final jobs to:",
        OUTPUT_FILE,
    )

    print(
        "Saved ranked jobs to:",
        FULL_OUTPUT_FILE,
    )

    print(
        "Saved rejected jobs to:",
        REJECTED_FILE,
    )

    print(
        "Saved rejection summary to:",
        REJECTION_SUMMARY_FILE,
    )


if __name__ == "__main__":
    main()