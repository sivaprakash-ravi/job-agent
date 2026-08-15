import json
import urllib.parse
import urllib.request
from pathlib import Path

from profile import TARGET_ROLES, SKILLS, LOCATIONS
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
        "category": "devops,sre,support,operations,software_engineering",
        "seniority": "junior,middle",
        "employment_type": "full_time",
        "posted_within_days": "3",
        "sort": "posted_at",
        "order": "desc",
        "limit": "100",
        "offset": "0",
    }

    url = API_URL + "?" + urllib.parse.urlencode(params)

    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "job-agent/1.0",
        },
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        data = json.loads(response.read().decode("utf-8"))

    return data.get("data", []), data.get("meta", {})


def load_indeed_jobs():
    if not INDEED_FILE.exists():
        return []

    try:
        with open(INDEED_FILE, "r", encoding="utf-8") as file:
            jobs = json.load(file)

        if not isinstance(jobs, list):
            return []

        return jobs

    except (json.JSONDecodeError, OSError):
        print("Warning: Could not read Indeed job report.")
        return []


def load_sent_jobs():
    if SENT_FILE.exists():
        try:
            with open(SENT_FILE, "r", encoding="utf-8") as file:
                return set(json.load(file))
        except (json.JSONDecodeError, OSError):
            pass

    return set()


def save_sent_jobs(sent_jobs):
    with open(SENT_FILE, "w", encoding="utf-8") as file:
        json.dump(
            sorted(sent_jobs),
            file,
            indent=2,
            ensure_ascii=False,
        )


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)

    # ---------------------------------------------------------
    # 1. Collect FreeHire jobs
    # ---------------------------------------------------------
    freehire_jobs, meta = collect_freehire_jobs()

    # ---------------------------------------------------------
    # 2. Load Indeed jobs collected by JobSpy
    # ---------------------------------------------------------
    indeed_jobs = load_indeed_jobs()

    # ---------------------------------------------------------
    # 3. Combine both sources
    # ---------------------------------------------------------
    all_jobs = freehire_jobs + indeed_jobs

    print("=" * 60)
    print("DAILY JOB AGENT")
    print("=" * 60)
    print(f"FreeHire jobs returned : {len(freehire_jobs)}")
    print(f"Indeed jobs returned   : {len(indeed_jobs)}")
    print(f"Combined raw jobs      : {len(all_jobs)}")
    print(f"FreeHire total matches : {meta.get('total', 'unknown')}")
    print()

    # ---------------------------------------------------------
    # 4. Run the SAME matcher against both sources
    # ---------------------------------------------------------
    ranked_jobs = rank_jobs(all_jobs)
    relevant_jobs = keep_relevant_jobs(ranked_jobs)

    # ---------------------------------------------------------
    # 5. Remove jobs already sent previously
    # ---------------------------------------------------------
    sent_jobs = load_sent_jobs()

    new_jobs = []

    for job in relevant_jobs:
        job_url = job.get("url") or job.get("job_url") or ""

        if job_url and job_url not in sent_jobs:
            new_jobs.append(job)
            sent_jobs.add(job_url)

    save_sent_jobs(sent_jobs)

    # ---------------------------------------------------------
    # 6. Save final Telegram report
    # ---------------------------------------------------------
    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
        json.dump(
            new_jobs,
            file,
            indent=2,
            ensure_ascii=False,
        )

    # Save everything that went through ranking.
    with open(FULL_OUTPUT_FILE, "w", encoding="utf-8") as file:
        json.dump(
            ranked_jobs,
            file,
            indent=2,
            ensure_ascii=False,
        )

    # ---------------------------------------------------------
    # 7. Print final results
    # ---------------------------------------------------------
    print(f"Jobs after matching : {len(relevant_jobs)}")
    print(f"New jobs to report  : {len(new_jobs)}")
    print(
        f"Previously seen/ignored: "
        f"{len(relevant_jobs) - len(new_jobs)}"
    )
    print()

    for index, job in enumerate(new_jobs[:20], start=1):
        title = job.get("title", "Unknown title")
        company = job.get(
            "company",
            job.get("company_name", "Unknown company"),
        )
        location = job.get("location", "Unknown location")
        job_url = job.get("url") or job.get("job_url", "")
        source = job.get("source", "FreeHire")

        print(
            f"{index}. {title} — "
            f"{job.get('match_score', 0)}% "
            f"({job.get('match_category', 'Match')})"
        )
        print(f"   Source   : {source}")
        print(f"   Company  : {company}")
        print(f"   Location : {location}")
        print(f"   URL      : {job_url}")
        print()

    print(f"Saved final jobs to : {OUTPUT_FILE}")
    print(f"Saved ranked jobs to: {FULL_OUTPUT_FILE}")
    print(f"Saved history to    : {SENT_FILE}")


if __name__ == "__main__":
    main()
