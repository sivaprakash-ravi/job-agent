"""Himalayas adapter.

Uses the public Himalayas jobs API:
https://himalayas.app/jobs/api
"""

from sources.base import fetch_json, normalize_common, REQUEST_TIMEOUT


MAX_JOBS = 300
HIMALAYAS_API = "https://himalayas.app/jobs/api"


def _fetch_page(params):
    return fetch_json(
        HIMALAYAS_API,
        timeout=REQUEST_TIMEOUT,
        max_bytes=6 * 1024 * 1024,
        params=params,
    )


def _extract_jobs(data):
    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        jobs = data.get("jobs")

        if isinstance(jobs, list):
            return jobs

    return None


def run(search_queries, locations=None):
    """Collect remote-first jobs from Himalayas."""
    result = {
        "provider": "himalayas",
        "status": "ok",
        "count": 0,
        "error": "",
        "jobs": [],
    }

    try:
        first_page = _fetch_page({})
    except Exception as error:
        result["status"] = "blocked"
        result["error"] = str(error)
        return result

    try:
        items = _extract_jobs(first_page)

        if items is None:
            result["status"] = "blocked"
            result["error"] = "Unexpected API response shape"
            return result

        next_cursor = None

        if isinstance(first_page, dict):
            next_cursor = first_page.get("nextCursor")

        while next_cursor and len(items) < MAX_JOBS:
            next_page = _fetch_page({"cursor": next_cursor})

            next_found = _extract_jobs(next_page)

            if not next_found:
                break

            items.extend(next_found)

            if isinstance(next_page, dict):
                next_cursor = next_page.get("nextCursor")
            else:
                next_cursor = None

        items = items[:MAX_JOBS]
    except Exception as error:
        result["status"] = "blocked"
        result["error"] = str(error)
        return result

    if not items:
        result["status"] = "ok" if isinstance(first_page, dict) else "blocked"
        result["error"] = "" if isinstance(first_page, dict) else "No jobs returned by API"
        result["count"] = 0
        result["jobs"] = []
        return result

    jobs = []

    for item in items:
        title = str(item.get("title") or "")

        if not title:
            continue

        description = str(item.get("description") or "")

        location_parts = (
            item.get("locationRestrictions")
            or item.get("timezoneRestrictions")
            or []
        )

        if isinstance(location_parts, str):
            location_text = location_parts
        else:
            location_text = ", ".join(
                str(part) for part in location_parts
            )

        if not location_text:
            location_text = "Remote"

        salary = ""

        minimum = item.get("minSalary")
        maximum = item.get("maxSalary")

        if minimum or maximum:
            salary = f"{minimum} - {maximum}".replace("None", "").replace(" -  ", " ")

        skills = item.get("categories") or []

        if not isinstance(skills, list):
            skills = []

        job = normalize_common(
            source="himalayas",
            source_job_id=str(item.get("guid") or ""),
            title=title,
            company=str(item.get("companyName") or ""),
            location=location_text,
            remote=True,
            url=str(item.get("applicationLink") or ""),
            description=description,
            date_posted=str(item.get("pubDate") or ""),
            employment_type=str(item.get("employmentType") or ""),
            salary=salary,
            skills=skills,
            search_query="",
            search_location="Remote",
            raw={
                "seniority": item.get("seniority"),
                "currency": item.get("currency"),
                "salaryPeriod": item.get("salaryPeriod"),
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