"""Remote OK adapter.

Uses the public Remote OK jobs API:
https://remoteok.com/api
"""

from sources.base import fetch_json, normalize_common


MAX_JOBS = 300


def run(search_queries, locations=None):
    """Collect remote jobs from Remote OK."""
    result = {
        "provider": "remoteok",
        "status": "ok",
        "count": 0,
        "error": "",
        "jobs": [],
    }

    try:
        data = fetch_json(
            "https://remoteok.com/api",
            max_bytes=6 * 1024 * 1024,
        )
    except Exception as error:
        result["status"] = "blocked"
        result["error"] = str(error)
        return result

    if not isinstance(data, list):
        result["status"] = "blocked"
        result["error"] = "Unexpected API response shape"
        return result

    jobs = []

    for item in data[1:MAX_JOBS + 1]:
        if not isinstance(item, dict):
            continue

        title = str(item.get("position") or "")

        if not title:
            continue

        url = str(item.get("url") or item.get("original") or "")

        if not url:
            slug = str(item.get("slug") or "")
            url = f"https://remoteok.com/remote-jobs/{slug}" if slug else ""

        skills = item.get("tags") or []

        if not isinstance(skills, list):
            skills = []

        job = normalize_common(
            source="remoteok",
            source_job_id=str(item.get("id") or ""),
            title=title,
            company=str(item.get("company") or ""),
            location="Remote",
            remote=True,
            url=url,
            description=(
                str(item.get("description") or "")
                if isinstance(item.get("description"), str)
                else ""
            ),
            date_posted=str(item.get("date") or ""),
            employment_type="full-time",
            skills=skills,
            search_query="",
            search_location="Remote",
            raw={
                "tags": skills,
                "slug": item.get("slug"),
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