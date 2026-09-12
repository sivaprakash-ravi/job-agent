"""Jobicy remote-jobs adapter.

Uses the public Jobicy JSON API:
https://jobicy.com/api/v2/remote-jobs?count=...&tag=...&industry=...
"""

import urllib.parse

from sources.base import (
    best_query,
    detect_remote,
    fetch_json,
    html_to_text,
    normalize_common,
)


API_URL = "https://jobicy.com/api/v2/remote-jobs"

MAX_QUERIES = 6
MAX_JOBS = 300


def run(search_queries, locations=None):
    """Collect remote jobs from Jobicy for each query."""
    result = {
        "provider": "jobicy",
        "status": "ok",
        "count": 0,
        "error": "",
        "jobs": [],
    }

    queries = search_queries[:MAX_QUERIES] or ["DevOps Engineer"]

    jobs = []

    for query in queries:
        url = API_URL + "?" + urllib.parse.urlencode(
            {
                "count": "30",
                "tag": query,
            }
        )

        try:
            data = fetch_json(url, max_bytes=8 * 1024 * 1024)
        except Exception as error:
            result["error"] = (
                f"{result['error']} ; {query}: {error}"
                if result["error"]
                else f"{query}: {error}"
            )
            continue

        for item in data.get("jobs") or []:
            title = str(item.get("jobTitle") or "")

            if not title:
                continue

            location = str(item.get("jobGeo") or "")
            remote = detect_remote(location) or location.lower() in (
                "remote",
                "worldwide",
                "anywhere",
            )

            if not location:
                location = "Remote" if remote else ""

            description = html_to_text(item.get("jobDescription"))

            salary = ""

            if item.get("salaryMin") or item.get("salaryMax"):
                salary = f"{item.get('salaryMin')} - {item.get('salaryMax')}"

                if item.get("salaryCurrency"):
                    salary += f" {item.get('salaryCurrency')}"

                if item.get("salaryPeriod"):
                    salary += f" per {item.get('salaryPeriod')}"

            job_types = item.get("jobType") or []

            if isinstance(job_types, str):
                employment_type = job_types
            else:
                employment_type = ", ".join(
                    str(entry)
                    for entry in job_types
                )

            job = normalize_common(
                source="jobicy",
                source_job_id=str(item.get("id") or ""),
                title=title,
                company=str(item.get("companyName") or ""),
                location=location,
                remote=True if remote else None,
                url=str(item.get("url") or ""),
                description=description,
                date_posted=str(item.get("pubDate") or ""),
                posted_at=str(item.get("lastModified") or "") or str(item.get("pubDate") or ""),
                employment_type=employment_type,
                salary=salary,
                skills=list(item.get("jobTags") or []),
                search_query=best_query(title, description, search_queries),
                search_location="Remote" if remote else location,
                json_ld=None,
                raw={
                    "jobIndustry": item.get("jobIndustry"),
                    "jobLevel": item.get("jobLevel"),
                    "jobTags": item.get("jobTags"),
                },
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

    result["jobs"] = unique[:MAX_JOBS]
    result["count"] = len(result["jobs"])

    return result