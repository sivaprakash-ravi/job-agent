import json
import urllib.parse
import urllib.request
from pathlib import Path
from profile import TARGET_ROLES, SKILLS, LOCATIONS
from job_matcher import keep_relevant_jobs, rank_jobs

API_URL = "https://freehire.me/api/v1/jobs/search"

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

jobs = data.get("data", [])
meta = data.get("meta", {})
ranked_jobs = rank_jobs(jobs)
jobs_to_report = keep_relevant_jobs(ranked_jobs)

output_dir = Path("reports")
output_dir.mkdir(exist_ok=True)

output_file = output_dir / "jobs.json"
full_output_file = output_dir / "all_ranked_jobs.json"

with open(output_file, "w", encoding="utf-8") as file:
    json.dump(jobs_to_report, file, indent=2, ensure_ascii=False)

with open(full_output_file, "w", encoding="utf-8") as file:
    json.dump(ranked_jobs, file, indent=2, ensure_ascii=False)

print("=" * 60)
print("DAILY JOB AGENT")
print("=" * 60)
print(f"Jobs returned: {len(jobs)}")
print(f"Total matching jobs: {meta.get('total', 'unknown')}")
print(f"Jobs kept after ranking: {len(jobs_to_report)}")
print(f"Jobs ignored: {len(ranked_jobs) - len(jobs_to_report)}")
print()

for index, job in enumerate(jobs_to_report[:20], start=1):
    title = job.get("title", "Unknown title")
    company = job.get("company", job.get("company_name", "Unknown company"))
    location = job.get("location", "Unknown location")
    job_url = job.get("url", "")

    print(f"{index}. {title} — {job['match_score']}% ({job['match_category']})")
    print(f"   Company : {company}")
    print(f"   Location: {location}")
    print(f"   URL     : {job_url}")
    print()

print(f"Saved job data to: {output_file}")
print(f"Saved full ranked data to: {full_output_file}")
