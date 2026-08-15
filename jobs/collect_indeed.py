import json
from pathlib import Path

from jobspy import scrape_jobs


SEARCH_TERM = "software engineer"
LOCATION = "Bangalore"


def main():
    print("=" * 60)
    print("INDEED JOB SEARCH - JOBSPY")
    print("=" * 60)

    jobs = scrape_jobs(
        site_name=["indeed"],
        search_term=SEARCH_TERM,
        location=LOCATION,
        results_wanted=10,
        country_indeed="India",
        hours_old=72,
        verbose=1,
    )

    normalized_jobs = []

    for _, job in jobs.iterrows():
        normalized_jobs.append(
            {
                "source": "indeed",
                "title": job.get("title", ""),
                "company": job.get("company", ""),
                "location": job.get("location", ""),
                "description": job.get("description", ""),
                "job_url": job.get("job_url", ""),
                "job_type": job.get("job_type", ""),
                "date_posted": str(job.get("date_posted", "")),
                "is_remote": job.get("is_remote", False),
            }
        )

    output_dir = Path("reports")
    output_dir.mkdir(exist_ok=True)

    output_file = output_dir / "indeed_jobs.json"

    with open(output_file, "w", encoding="utf-8") as file:
        json.dump(
            normalized_jobs,
            file,
            indent=2,
            ensure_ascii=False,
        )

    print()
    print(f"Indeed jobs returned: {len(normalized_jobs)}")
    print(f"Saved to: {output_file}")
    print()

    for index, job in enumerate(normalized_jobs[:10], start=1):
        print(
            f"{index}. {job['title']} | "
            f"{job['company']} | "
            f"{job['location']}"
        )


if __name__ == "__main__":
    main()
