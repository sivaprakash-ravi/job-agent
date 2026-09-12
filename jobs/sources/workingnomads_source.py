"""Working Nomads adapter.

Uses the public Working Nomads jobs API:
https://www.workingnomads.com/api/exposed_jobs/
"""

from sources.base import fetch_json, normalize_common


MAX_JOBS = 200


def run(search_queries, locations=None):
    """Collect remote jobs from Working Nomads."""
    result = {
        "provider": "workingnomads",
        "status": "ok",
        "count": 0,
        "error": "",
        "jobs": [],
    }

    try:
        data = fetch_json(
            "https://www.workingnomads.com/api/exposed_jobs/",
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

    for item in data[:MAX_JOBS]:
        title = str(item.get("title") or "")

        if not title:
            continue

        skills = str(item.get("tags") or "")

        skills_list = [
            part.strip()
            for part in skills.split(",")
            if part.strip()
        ]

        job = normalize_common(
            source="workingnomads",
            source_job_id="",
            title=title,
            company=str(item.get("company_name") or ""),
            location=str(item.get("location") or "Remote"),
            remote=True,
            url=str(item.get("url") or ""),
            description=str(item.get("description") or ""),
            date_posted=str(item.get("pub_date") or ""),
            employment_type="",
            skills=skills_list,
            search_query=(
                str(item.get("category_name") or "")
            ),
            search_location="Remote",
            raw={
                "category_name": item.get("category_name"),
                "tags": skills_list,
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