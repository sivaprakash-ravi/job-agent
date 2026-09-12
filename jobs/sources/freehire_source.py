"""FreeHire adapter.

FreeHire feeds jobs from sources such as Indeed and LinkedIn through
its public search API.
"""

import urllib.parse

from profile import LOCATIONS

from sources.base import normalize_common


API_URL = "https://freehire.me/api/v1/jobs/search"

MAX_QUERIES = 8
LIMIT = 80


def run(search_queries, locations=None):
    """Collect jobs from FreeHire for each query."""
    result = {
        "provider": "freehire",
        "status": "ok",
        "count": 0,
        "error": "",
        "jobs": [],
    }

    if locations is None:
        locations = [loc for loc in LOCATIONS if loc]

    has_remote = any(str(loc).lower() == "remote" for loc in locations)

    queries = search_queries[:MAX_QUERIES]

    jobs = []

    for query in queries:
        for remote_flag in ([False, True] if has_remote else [False]):
            params = {
                "q": query,
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
                "limit": str(LIMIT),
                "offset": "0",
            }

            if remote_flag:
                params["remote"] = "true"
                search_location = "Remote"
            else:
                search_location = ", ".join(locations)

            url = API_URL + "?" + urllib.parse.urlencode(params)

            try:
                import requests

                response = requests.get(
                    url,
                    headers={
                        "Accept": "application/json",
                        "User-Agent": "job-agent/2.0",
                    },
                    timeout=30,
                )

                response.raise_for_status()

                data = response.json()
            except Exception as error:
                result["error"] = (
                    f"{result['error']} ; {error}"
                    if result["error"]
                    else str(error)
                )
                continue

            for item in data.get("data", []):
                company = (
                    item.get("company_name")
                    or item.get("company")
                    or ""
                )

                if isinstance(company, dict):
                    company = (
                        company.get("name")
                        or company.get("title")
                        or ""
                    )

                skill_list = item.get("skills")

                if not isinstance(skill_list, list):
                    skill_list = []

                job = normalize_common(
                    source="freehire",
                    source_job_id=str(item.get("id") or item.get("external_id") or ""),
                    title=item.get("title") or "",
                    company=company,
                    location=(
                        item.get("location")
                        or item.get("city")
                        or ""
                    ),
                    remote=bool(item.get("is_remote") or remote_flag),
                    url=item.get("job_url") or item.get("url") or "",
                    description=item.get("description") or "",
                    date_posted=item.get("posted_at") or item.get("created_at") or "",
                    employment_type=item.get("employment_type") or "",
                    salary=item.get("salary") or "",
                    skills=skill_list,
                    search_query=query,
                    search_location=search_location,
                    raw=item,
                )

                if job["title"] and job["company"]:
                    jobs.append(job)

    seen = set()
    unique = []

    for job in jobs:
        key = job["url"] or job["source_job_id"]

        if not key or key in seen:
            continue

        seen.add(key)
        unique.append(job)

    result["jobs"] = unique
    result["count"] = len(unique)

    return result