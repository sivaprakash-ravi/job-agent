import json
from pathlib import Path

from jobspy import scrape_jobs


SEARCH_TERM = "software engineer"
LOCATION = "Bangalore"


def main():
    print("=" * 60)
    print("INDEED JOB SEARCH TEST - JOBSPY")
    print("=" * 60)
    print(f"Search: {SEARCH_TERM}")
    print(f"Location: {LOCATION}")
    print()

    jobs = scrape_jobs(
        site_name=["indeed"],
        search_term=SEARCH_TERM,
        location=LOCATION,
        results_wanted=10,
        country_indeed="India",
        hours_old=72,
        verbose=1,
    )

    output_dir = Path("reports")
    output_dir.mkdir(exist_ok=True)

    output_file = output_dir / "indeed_jobs.json"

    jobs.to_json(
        output_file,
        orient="records",
        indent=2,
        force_ascii=False,
    )

    print()
    print(f"Jobs returned: {len(jobs)}")
    print(f"Saved to: {output_file}")
    print()

    for index, (_, job) in enumerate(jobs.head(10).iterrows(), start=1):
        print(f"{index}. {job.get('title', 'Unknown title')}")
        print(f"   Company : {job.get('company', 'Unknown company')}")
        print(f"   Location: {job.get('location', 'Unknown location')}")
        print(f"   URL     : {job.get('job_url', '')}")
        print()


if __name__ == "__main__":
    main()
