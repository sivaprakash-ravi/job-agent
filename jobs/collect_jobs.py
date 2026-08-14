import json
import urllib.parse
import urllib.request
from pathlib import Path

API_URL = "https://freehire.me/api/v1/jobs/search"

params = {
    "countries": "IN",
    "posted_within_days": "3",
    "sort": "posted_at",
    "order": "desc",
    "limit": "100",
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

output_dir = Path("reports")
output_dir.mkdir(exist_ok=True)

output_file = output_dir / "jobs.json"

with open(output_file, "w", encoding="utf-8") as file:
    json.dump(jobs, file, indent=2, ensure_ascii=False)

print(f"Found {len(jobs)} jobs.")

for index, job in enumerate(jobs[:20], start=1):
    print(f"{index}. {job.get('title', 'Unknown title')}")
    print(f"   Company: {job.get('company_name', 'Unknown company')}")
    print(f"   Location: {job.get('location', 'Unknown location')}")
    print(f"   URL: {job.get('url', '')}")
    print()
