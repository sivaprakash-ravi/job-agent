"""Remotive remote-jobs adapter.

Uses the public Remotive API:
https://remotive.com/api/remote-jobs?search=...&limit=...
"""

import urllib.parse

from sources.base import (
    best_query,
    detect_remote,
    fetch_json,
    html_to_text,
    normalize_common,
)


API_URL = "https://remotive.com/api/remote-jobs"

MAX_QUERIES = 8
MAX_JOBS = 300


def run(search_queries, locations=None):
    """Collect remote jobs from Remotive for each query."""
    result = {
        "provider": "remotive",
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
                "search": query,
                "limit": "30",
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
            title = str(item.get("title") or "")

            if not title:
                continue

            location = str(item.get("candidate_required_location") or "")
            remote = detect_remote(location) or location.lower() in ("worldwide", "remote")

            if not location:
                location = "Remote" if remote else ""

            description = html_to_text(item.get("description"))

            job = normalize_common(
                source="remotive",
                source_job_id=str(item.get("id") or ""),
                title=title,
                company=str(item.get("company_name") or ""),
                location=location,
                remote=True if remote else None,
                url=str(item.get("url") or ""),
                description=description,
                date_posted=str(item.get("publication_date") or ""),
                posted_at=str(item.get("publication_date") or ""),
                employment_type=str(item.get("job_type") or "").replace("_", "-"),
                salary=str(item.get("salary") or ""),
                skills=list(item.get("tags") or []),
                search_query=best_query(title, description, search_queries),
                search_location="Remote" if remote else location,
                json_ld=None,
                raw={
                    "category": item.get("category"),
                    "tags": item.get("tags"),
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