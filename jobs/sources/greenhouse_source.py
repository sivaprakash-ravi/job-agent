"""Greenhouse ATS adapter.

Uses the public Greenhouse boards API:
https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs
"""

from sources.base import fetch_json, normalize_common, best_query


MAX_BOARDS = 12
MAX_JOBS = 500

GREENHOUSE_BOARDS = [
    "google",
    "stripe",
    "cloudflare",
    "dropbox",
    "github",
    "gitlab",
    "airbnb",
    "instacart",
    "coinbase",
    "datadog",
    "snowflake",
    "linkedin",
]


def run(search_queries, locations=None):
    """Collect public Greenhouse job postings."""
    result = {
        "provider": "greenhouse",
        "status": "ok",
        "count": 0,
        "error": "",
        "jobs": [],
    }

    jobs = []

    for board in GREENHOUSE_BOARDS[:MAX_BOARDS]:
        url = (
            f"https://boards-api.greenhouse.io/v1/boards/"
            f"{board}/jobs?content=true&per_page=100"
        )

        try:
            data = fetch_json(url, max_bytes=6 * 1024 * 1024)
        except Exception as error:
            result["error"] = (
                f"{result['error']} ; {board}: {error}"
                if result["error"]
                else f"{board}: {error}"
            )
            continue

        for item in data.get("jobs", []):
            title = str(item.get("title") or "")

            if not title:
                continue

            location_obj = item.get("location") or {}
            location_name = (
                location_obj.get("name")
                if isinstance(location_obj, dict)
                else str(location_obj or "")
            )

            location_lower = str(location_name).lower()

            remote = any(
                token in location_lower
                for token in ("remote", "anywhere", "work from home", "wfh")
            )

            content = item.get("content") or ""

            query = best_query(title, content, search_queries)

            job = normalize_common(
                source="greenhouse",
                source_job_id=str(item.get("id") or item.get("internal_job_id") or ""),
                title=title,
                company=(
                    item.get("company_name")
                    or board.capitalize()
                ),
                location=location_name or "Remote",
                remote=remote,
                url=item.get("absolute_url") or "",
                description=content,
                date_posted=item.get("first_published") or item.get("updated_at") or "",
                employment_type=item.get("employment_type") or "",
                search_query=query,
                search_location="Remote" if remote else location_name,
                raw={
                    "requisition_id": item.get("requisition_id"),
                    "departments": item.get("departments"),
                    "offices": item.get("offices"),
                    "employment_type": item.get("employment_type"),
                },
            )

            jobs.append(job)

    seen = set()
    unique = []

    for job in jobs:
        key = job["url"] or job["source_job_id"]

        if key in seen:
            continue

        seen.add(key)
        unique.append(job)

    results = unique[:MAX_JOBS]

    result["jobs"] = results
    result["count"] = len(results)

    return result