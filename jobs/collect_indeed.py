import json
import os
import urllib.parse
import urllib.request
from pathlib import Path


API_URL = "https://indeed-scraper.omkar.cloud/indeed/search"

SEARCH_TERM = "software engineer"
LOCATION = ""


def main():
    api_key = os.environ["INDEED_API_KEY"]

    params = {
        "search_term": SEARCH_TERM,
        "location": LOCATION,
        "page": "1",
    }

    url = API_URL + "?" + urllib.parse.urlencode(params)

    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "API-Key": api_key,
            "User-Agent": "job-agent/1.0",
        },
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        data = json.loads(response.read().decode("utf-8"))

    print("API response:")
    print(json.dumps(data, indent=2, ensure_ascii=False))

    if "message" in data and "jobs" not in data:
        print()
        print("Indeed API did not return job results.")
        print(f"Indeed message: {data.get('message')}")
        print("No Indeed jobs will be reported from this run.")
        return

    jobs = data.get("jobs", [])

    output_dir = Path("reports")
    output_dir.mkdir(exist_ok=True)

    output_file = output_dir / "indeed_jobs.json"

    with open(output_file, "w", encoding="utf-8") as file:
        json.dump(jobs, file, indent=2, ensure_ascii=False)

    print("=" * 60)
    print("INDEED JOB SEARCH TEST")
    print("=" * 60)
    print(f"Search: {SEARCH_TERM}")
    print(f"Location: {LOCATION}")
    print(f"Jobs returned: {len(jobs)}")
    print(f"Saved to: {output_file}")
    print()

    for index, job in enumerate(jobs[:10], start=1):
        print(f"{index}. {job.get('title', 'Unknown title')}")
        print(f"   Company : {job.get('company', 'Unknown company')}")
        print(f"   Location: {job.get('location', 'Unknown location')}")
        print(f"   URL     : {job.get('job_url', '')}")
        print()


if __name__ == "__main__":
    main()
