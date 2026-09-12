"""Workable ATS adapter.

Uses the public, unauthenticated Workable search API:
https://jobs.workable.com/api/v1/jobs?query=...&limit=...&nextPageToken=...

This single endpoint spans thousands of companies hosted on Workable
(an ATS), giving broad ATS-first coverage without board scraping.

Per-company widget accounts are also supported through the public
widget endpoint as a secondary, focused source.
"""

import urllib.parse

from sources.ats_registry import WORKABLE_ACCOUNTS
from sources.base import (
    best_query,
    detect_remote,
    fetch_json,
    html_to_text,
    normalize_common,
)


SEARCH_URL = "https://jobs.workable.com/api/v1/jobs"

SEARCH_LIMIT = "20"

WIDGET_URL = ( 
    "https://apply.workable.com/api/v1/widget/accounts/{account}"
)

MAX_QUERIES = 8
MAX_JOBS = 400

MAX_WIDGET_JOBS = 200

RETRYABLE_STATUSES = {400, 429, 500, 502, 503, 504}


def _fetch_with_retry(url, attempts=2, delay=1.5):
    """Fetch JSON with a single retry on transient failures."""
    last_error = None

    for attempt in range(attempts):
        try:
            return fetch_json(url, max_bytes=8 * 1024 * 1024)
        except Exception as error:
            last_error = error

            if attempt < attempts - 1:
                import time

                time.sleep(delay)

    raise last_error


def _run_search(search_queries):
    """Query the public Workable search API with pagination."""
    collected = []
    errors = []

    queries = search_queries[:MAX_QUERIES] or ["DevOps Engineer"]

    for query in queries:
        url = SEARCH_URL + "?" + urllib.parse.urlencode(
            {
                "query": query,
                "limit": SEARCH_LIMIT,
            }
        )

        page = 0

        while url and page < 4:
            try:
                data = _fetch_with_retry(url)
            except Exception as error:
                errors.append(f"{query}: {error}")
                break

            items = data.get("jobs") or []

            for item in items:
                if str(item.get("state") or "published").lower() != "published":
                    continue

                title = str(item.get("title") or "")

                if not title:
                    continue

                collected.append(
                    _normalize_item(
                        query,
                        item,
                    )
                )

            next_token = data.get("nextPageToken")

            if not next_token:
                break

            url = SEARCH_URL + "?" + urllib.parse.urlencode(
                {
                    "query": query,
                    "limit": SEARCH_LIMIT,
                    "nextPageToken": next_token,
                }
            )

            page += 1

    return collected, errors


def _clean_location_parts(parts):
    """Drop pseudo-locations such as TELECOMMUTE / REMOTE labels."""
    skip = {
        "telecommute",
        "remote",
        "remote only",
        "worldwide",
        "anywhere",
        "nationwide",
        "flexible",
    }

    cleaned = []

    for part in parts:
        value = str(part or "").strip()

        if not value:
            continue

        if value.lower() in skip:
            continue

        cleaned.append(value)

    return cleaned


def _extract_location(item):
    """Build a readable location string from Workable fields."""
    location_raw = item.get("location")
    locations_raw = item.get("locations") or []

    parts = []

    if isinstance(location_raw, dict):
        composite = ", ".join(
            dict.fromkeys(
                value.strip()
                for value in (
                    location_raw.get("city"),
                    location_raw.get("subregion"),
                    location_raw.get("region"),
                    location_raw.get("countryName"),
                    location_raw.get("name"),
                )
                if isinstance(value, str) and value.strip()
            )
        )

        if composite:
            parts.append(composite)

    elif isinstance(location_raw, str):
        parts.append(location_raw)

    parts = _clean_location_parts(parts)

    if isinstance(locations_raw, list):
        parts.extend(
            _clean_location_parts(locations_raw)
        )

    return ", ".join(dict.fromkeys(part for part in parts if part))


def _company_name(item):
    """Extract the company display name from a Workable item."""
    company_raw = item.get("company")

    if isinstance(company_raw, dict):
        for key in ("title", "name"):
            value = company_raw.get(key)

            if isinstance(value, str) and value.strip():
                return value.strip()

        return ""

    if isinstance(company_raw, list):
        for entry in company_raw:
            if isinstance(entry, dict):
                for key in ("title", "name"):
                    value = entry.get(key)

                    if isinstance(value, str) and value.strip():
                        return value.strip()

        return ""

    return str(company_raw or "").strip()


def _normalize_item(query, item):
    """Convert one Workable search item into the common schema."""
    title = str(item.get("title") or "")
    company = _company_name(item)
    location = _extract_location(item)

    workplace = str(item.get("workplace") or "")
    remote = detect_remote(location, workplace)

    if not location and remote:
        location = "Remote"

    description = "\n".join(
        part
        for part in (
            html_to_text(item.get("description")),
            html_to_text(item.get("requirementsSection")),
            html_to_text(item.get("benefitsSection")),
        )
        if part
    )

    employment_type = str(item.get("employmentType") or "")

    if "full" in employment_type.lower():
        employment_type = "full-time"
    elif "part" in employment_type.lower():
        employment_type = "part-time"

    return normalize_common(
        source="workable",
        source_job_id=str(item.get("id") or ""),
        title=title,
        company=company,
        location=location,
        remote=remote,
        url=str(item.get("url") or item.get("applyUrl") or ""),
        apply_url=str(item.get("applyUrl") or item.get("url") or ""),
        description=description,
        requirements=html_to_text(item.get("requirementsSection")),
        date_posted=str(item.get("created") or ""),
        posted_at=str(item.get("updated") or "") or str(item.get("created") or ""),
        employment_type=employment_type,
        search_query=query,
        search_location="Remote" if remote else location,
        json_ld=None,
        raw={
            "workplace": workplace,
            "language": item.get("language"),
            "isFeatured": item.get("isFeatured"),
            "departments": item.get("department"),
        },
    )


def _run_widget(search_queries, locations=None):
    """Collect jobs from configured public Workable widget accounts."""
    collected = []
    errors = []

    for account in WORKABLE_ACCOUNTS:
        url = WIDGET_URL.format(account=account)

        try:
            data = _fetch_with_retry(url)
        except Exception as error:
            errors.append(f"{account}: {error}")
            continue

        for item in data.get("jobs") or []:
            title = str(item.get("title") or "")

            if not title:
                continue

            location = _extract_location(item)
            workplace = str(item.get("workplace") or "")
            remote = detect_remote(location, workplace)

            if not location and remote:
                location = "Remote"

            if not location:
                location = str(account)

            content = html_to_text(item.get("description"))

            employment_type = str(item.get("employmentType") or "")

            if "full" in employment_type.lower():
                employment_type = "full-time"
            elif "part" in employment_type.lower():
                employment_type = "part-time"

            collected.append(
                normalize_common(
                    source="workable",
                    source_job_id=str(item.get("id") or ""),
                    title=title,
                    company=str(data.get("name") or account),
                    location=location,
                    remote=remote,
                    url=str(item.get("url") or item.get("applyUrl") or ""),
                    apply_url=str(item.get("applyUrl") or item.get("url") or ""),
                    description=content,
                    date_posted=str(item.get("created") or ""),
                    employment_type=employment_type,
                    search_query=best_query(
                        title,
                        content,
                        search_queries,
                    ),
                    search_location="Remote" if remote else location,
                    raw={"account": account},
                )
            )

    return collected, errors


def run(search_queries, locations=None):
    """Collect public Workable job postings."""
    result = {
        "provider": "workable",
        "status": "ok",
        "count": 0,
        "error": "",
        "jobs": [],
    }

    collected, search_errors = _run_search(search_queries)

    widget_jobs, widget_errors = _run_widget(
        search_queries,
        locations,
    )

    collected.extend(widget_jobs)

    errors = list(search_errors) + list(widget_errors)

    jobs = []
    seen = set()

    for job in collected:

        if not job.get("title"):
            continue

        key = job.get("url") or job.get("source_job_id")

        if not key or key in seen:
            continue

        seen.add(key)
        jobs.append(job)

    jobs = jobs[:MAX_JOBS]

    result["jobs"] = jobs
    result["count"] = len(jobs)

    if errors:
        result["error"] = "; ".join(errors[:3])

    if not jobs and errors:
        result["status"] = "error"

    return result