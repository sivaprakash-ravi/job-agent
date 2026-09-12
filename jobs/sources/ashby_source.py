"""Ashby ATS adapter.

Uses the public Ashby posting API:
https://api.ashbyhq.com/posting-api/job-board/{company}
"""

from sources.ats_registry import ASHBY_COMPANIES
from sources.base import fetch_json, normalize_common, best_query


MAX_COMPANIES = len(ASHBY_COMPANIES)
MAX_JOBS = 500


def run(search_queries, locations=None):
    """Collect public Ashby job postings."""
    result = {
        "provider": "ashby",
        "status": "ok",
        "count": 0,
        "error": "",
        "jobs": [],
    }

    jobs = []

    for company in ASHBY_COMPANIES[:MAX_COMPANIES]:
        url = (
            f"https://api.ashbyhq.com/posting-api/job-board/"
            f"{company}"
        )

        try:
            data = fetch_json(url, max_bytes=6 * 1024 * 1024)
        except Exception as error:
            result["error"] = (
                f"{result['error']} ; {company}: {error}"
                if result["error"]
                else f"{company}: {error}"
            )
            continue

        postings = data.get("jobPostings")

        if not isinstance(postings, list):
            postings = data.get("jobs")

        postings = postings or []

        for item in postings:
            if item.get("isListed") is False:
                continue

            title = str(item.get("title") or "")

            if not title:
                continue

            location = str(item.get("location") or "")

            secondary = item.get("secondaryLocations") or []
            secondary_text = ", ".join(
                str(secondary_item.get("location") or "")
                for secondary_item in secondary
                if isinstance(secondary_item, dict)
            )

            location_text = ", ".join(
                part
                for part in (location, secondary_text)
                if part
            )

            if not location_text and item.get("isRemote"):
                location_text = "Remote"

            query = best_query(
                title,
                item.get("descriptionPlain") or "",
                search_queries,
            )

            salary = ""

            if item.get("compensation"):
                compensation = item["compensation"]
                if isinstance(compensation, dict) and compensation.get("summary"):
                    salary = str(compensation["summary"])

            job = normalize_common(
                source="ashby",
                source_job_id=str(item.get("id") or ""),
                title=title,
                company=(
                    item.get("company")
                    or str(company)
                ),
                location=location_text,
                remote=bool(item.get("isRemote")),
                url=item.get("jobUrl") or item.get("applyUrl") or "",
                description=item.get("descriptionPlain") or "",
                date_posted=item.get("publishedAt") or "",
                employment_type=item.get("employmentType") or "",
                salary=salary,
                search_query=query,
                search_location=(
                    "Remote"
                    if item.get("isRemote")
                    else location_text
                ),
                raw={
                    "department": item.get("department"),
                    "team": item.get("team"),
                    "workplaceType": item.get("workplaceType"),
                    "employmentType": item.get("employmentType"),
                },
            )

            jobs.append(job)

    seen = set()
    unique = []

    for job in jobs:
        key = job["url"] or job["source_job_id"]

        if not key or key in seen:
            continue

        seen.add(key)
        unique.append(job)

    results = unique[:MAX_JOBS]

    result["jobs"] = results
    result["count"] = len(results)

    return result