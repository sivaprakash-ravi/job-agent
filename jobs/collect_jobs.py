"""Collect, enrich, filter and prepare jobs for Telegram."""

import json
import urllib.parse
import urllib.request
from pathlib import Path

from profile import TARGET_ROLES, SKILLS

from job_enricher import enrich_jobs

from job_matcher import (
    keep_relevant_jobs,
    rank_jobs,
    get_rejected_jobs,
)


API_URL = "https://freehire.me/api/v1/jobs/search"

OUTPUT_DIR = Path("reports")

INDEED_FILE = OUTPUT_DIR / "indeed_jobs.json"

OUTPUT_FILE = OUTPUT_DIR / "jobs.json"

FULL_OUTPUT_FILE = (
    OUTPUT_DIR / "all_ranked_jobs.json"
)

REJECTED_OUTPUT_FILE = (
    OUTPUT_DIR / "rejected_jobs.json"
)

UNVERIFIED_OUTPUT_FILE = (
    OUTPUT_DIR / "unverified_jobs.json"
)

SENT_FILE = (
    OUTPUT_DIR / "sent_jobs.json"
)


# ============================================================
# FREEHIRE
# ============================================================

def collect_freehire_jobs():
    """Collect jobs from FreeHire."""

    params = {
        "q": " ".join(
            TARGET_ROLES + SKILLS
        ),
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
            "User-Agent": "job-agent/2.0",
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


# ============================================================
# JOBSPY
# ============================================================

def load_jobspy_jobs():
    """Load jobs previously collected by JobSpy."""

    if not INDEED_FILE.exists():
        return []

    try:

        with open(
            INDEED_FILE,
            "r",
            encoding="utf-8",
        ) as file:

            data = json.load(file)

        if not isinstance(
            data,
            list,
        ):
            return []

        return data

    except (
        json.JSONDecodeError,
        OSError,
    ):

        print(
            "Warning: unable to read "
            "JobSpy report."
        )

        return []


# ============================================================
# HISTORY
# ============================================================

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


def save_sent_jobs(
    sent_jobs,
):
    """Save previously sent job identities."""

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


# ============================================================
# JSON
# ============================================================

def save_json(
    path,
    data,
):
    """Save JSON report."""

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


# ============================================================
# IDENTITY / DEDUPLICATION
# ============================================================

def job_identity(job):
    """
    Build a stable job identity.

    URL is preferred.
    Company + title is used as fallback.
    """

    url = (
        job.get("url")
        or job.get("job_url")
        or ""
    )

    if url:
        return url.strip().lower()

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
        .strip()
        .lower()
    )


def deduplicate_jobs(jobs):
    """Remove duplicate jobs across sources."""

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

        seen.add(
            identity
        )

        unique_jobs.append(
            job
        )

    return unique_jobs


# ============================================================
# VERIFICATION HELPERS
# ============================================================

def is_detail_verified(job):
    """
    Determine whether the actual job page was
    successfully fetched.
    """

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


# ============================================================
# MAIN
# ============================================================

def main():

    OUTPUT_DIR.mkdir(
        exist_ok=True
    )

    print()
    print("=" * 70)
    print("SIVA JOB AGENT — V1")
    print("=" * 70)

    # --------------------------------------------------------
    # 1. DISCOVERY
    # --------------------------------------------------------

    print()
    print(
        "[1/7] Collecting FreeHire jobs..."
    )

    try:

        (
            freehire_jobs,
            freehire_meta,
        ) = collect_freehire_jobs()

    except Exception as error:

        print(
            f"FreeHire collection failed: "
            f"{error}"
        )

        freehire_jobs = []
        freehire_meta = {}

    print(
        f"       FreeHire jobs: "
        f"{len(freehire_jobs)}"
    )

    print()
    print(
        "[2/7] Loading JobSpy jobs..."
    )

    jobspy_jobs = (
        load_jobspy_jobs()
    )

    print(
        f"       JobSpy jobs: "
        f"{len(jobspy_jobs)}"
    )

    # --------------------------------------------------------
    # 2. COMBINE
    # --------------------------------------------------------

    print()
    print(
        "[3/7] Combining and deduplicating..."
    )

    raw_jobs = (
        freehire_jobs
        + jobspy_jobs
    )

    raw_jobs = deduplicate_jobs(
        raw_jobs
    )

    print(
        f"       Unique jobs: "
        f"{len(raw_jobs)}"
    )

    # --------------------------------------------------------
    # 3. ENRICH
    # --------------------------------------------------------

    print()
    print(
        "[4/7] Fetching full available "
        "job details..."
    )

    enriched_jobs = enrich_jobs(
        raw_jobs
    )

    verified_count = sum(
        1
        for job in enriched_jobs
        if is_detail_verified(
            job
        )
    )

    unverified_count = (
        len(enriched_jobs)
        - verified_count
    )

    print(
        f"       Successfully fetched: "
        f"{verified_count}"
    )

    print(
        f"       Could not fetch: "
        f"{unverified_count}"
    )

    # --------------------------------------------------------
    # 4. MATCH
    # --------------------------------------------------------

    print()
    print(
        "[5/7] Running deep job matching..."
    )

    ranked_jobs = rank_jobs(
        enriched_jobs
    )

    # --------------------------------------------------------
    # 5. FINAL FILTER
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

    # --------------------------------------------------------
    # 6. UNVERIFIED
    # --------------------------------------------------------

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
    # SAVE COMPLETE RANKED REPORT
    # --------------------------------------------------------

    save_json(
        FULL_OUTPUT_FILE,
        ranked_jobs,
    )

    # --------------------------------------------------------
    # SAVE REJECTED REPORT
    # --------------------------------------------------------

    save_json(
        REJECTED_OUTPUT_FILE,
        rejected_jobs,
    )

    # --------------------------------------------------------
    # SAVE UNVERIFIED REPORT
    # --------------------------------------------------------

    save_json(
        UNVERIFIED_OUTPUT_FILE,
        unverified_jobs,
    )

    # --------------------------------------------------------
    # 7. REMOVE PREVIOUSLY SENT
    # --------------------------------------------------------

    print()
    print(
        "[6/7] Checking previously sent jobs..."
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
    # FINAL TELEGRAM DATA
    # --------------------------------------------------------

    save_json(
        OUTPUT_FILE,
        new_jobs,
    )

    # --------------------------------------------------------
    # REPORT
    # --------------------------------------------------------

    print()
    print(
        "[7/7] V1 filtering completed."
    )

    print()
    print("=" * 70)
    print("V1 RESULTS")
    print("=" * 70)

    print(
        f"Discovered jobs       : "
        f"{len(raw_jobs)}"
    )

    print(
        f"Enriched jobs         : "
        f"{len(enriched_jobs)}"
    )

    print(
        f"Detail verified       : "
        f"{verified_count}"
    )

    print(
        f"Detail unavailable    : "
        f"{unverified_count}"
    )

    print(
        f"Eligible jobs         : "
        f"{len(relevant_jobs)}"
    )

    print(
        f"Rejected jobs         : "
        f"{len(rejected_jobs)}"
    )

    print(
        f"Unverified jobs       : "
        f"{len(unverified_jobs)}"
    )

    print(
        f"New Telegram jobs     : "
        f"{len(new_jobs)}"
    )

    print()

    print(
        "Reports created:"
    )

    print(
        f"  ✓ {OUTPUT_FILE}"
    )

    print(
        f"  ✓ {FULL_OUTPUT_FILE}"
    )

    print(
        f"  ✓ {REJECTED_OUTPUT_FILE}"
    )

    print(
        f"  ✓ {UNVERIFIED_OUTPUT_FILE}"
    )

    print(
        f"  ✓ {SENT_FILE}"
    )

    print()

    print(
        "FreeHire total matches:",
        freehire_meta.get(
            "total",
            "unknown",
        ),
    )


if __name__ == "__main__":
    main()