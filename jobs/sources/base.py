"""Shared helpers, search-term building and the common job schema.

Every source adapter normalizes its raw payloads into the common
schema defined by :func:`normalize_common` and returns a result dict::

    {
        "provider": "name",
        "status": "ok" | "blocked" | "unavailable" | "error",
        "count": <int>,
        "error": "<description>",
        "jobs": [ <common schema jobs> ],
    }

profile.py remains the single source of truth for roles, skills,
locations and preferences.
"""

import requests

from profile import LOCATIONS, SKILLS, TARGET_ROLES


REQUEST_TIMEOUT = 20
PROBE_TIMEOUT = 10
MAX_RESPONSE_BYTES = 6 * 1024 * 1024

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0 Safari/537.36"
)

HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/json,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def build_search_queries(limit=None):
    """Build multiple focused search queries from profile.py.

    Uses role families plus the configured TARGET_ROLES and a
    sensible subset of the configured skills. Never one giant
    Boolean query.
    """
    broad = [
        "DevOps",
        "DevOps Engineer",
        "Cloud Engineer",
        "Cloud Support",
        "Cloud Operations",
        "SRE",
        "Site Reliability",
        "Infrastructure",
        "System Administrator",
        "Systems Engineer",
        "IT Operations",
        "IT Support",
        "Technical Support",
        "Application Support",
        "Production Support",
        "NOC",
        "Monitoring",
        "QA",
        "Quality Assurance",
        "QA Engineer",
        "Software Tester",
        "Test Engineer",
        "Automation Tester",
    ]

    skill_queries = [
        skill
        for skill in SKILLS
        if skill.lower()
        in {
            "gcp",
            "aws",
            "azure",
            "linux",
            "docker",
            "kubernetes",
            "python",
            "java",
            "sql",
            "ci/cd",
        }
    ]

    queries = [q.strip() for q in broad + TARGET_ROLES + skill_queries]
    queries = [q for q in queries if q]

    unique = list(dict.fromkeys(queries))

    if limit is not None and limit > 0:
        return unique[:limit]

    return unique


def build_locations():
    """Return all locations configured in profile.py.

    Remote is included whenever it is configured in profile.py.
    """
    locations = [str(location).strip() for location in LOCATIONS]
    locations = [location for location in locations if location]

    if not locations:
        locations = ["Chennai"]

    return locations


def best_query(title, description, queries):
    """Choose the first query whose terms appear in title/description."""
    haystack = f"{title} {description}".lower()

    for query in queries:
        terms = query.lower().split()
        if all(term in haystack for term in terms):
            return query

    return ""


def fetch_text(url, timeout=REQUEST_TIMEOUT, max_bytes=MAX_RESPONSE_BYTES):
    """Fetch a URL and return its text with sensible limits."""
    response = requests.get(url, headers=HEADERS, timeout=timeout)

    response.raise_for_status()

    content = response.content

    if max_bytes and len(content) > max_bytes:
        content = content[:max_bytes]

    return content.decode("utf-8", errors="ignore")


def fetch_json(
    url,
    timeout=REQUEST_TIMEOUT,
    max_bytes=MAX_RESPONSE_BYTES,
    params=None,
):
    """Fetch a URL and parse it as JSON."""
    response = requests.get(
        url,
        headers=HEADERS,
        timeout=timeout,
        params=params,
    )

    response.raise_for_status()

    content = response.content

    if max_bytes and len(content) > max_bytes:
        content = content[:max_bytes]

    return response.json()


def probe_result(provider, url, blocked_reason):
    """Attempt one polite GET and report the honest outcome.

    Used for providers that are known to require authentication,
    captchas or other access controls. We never bypass protections;
    we just report exactly what happened.
    """
    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=PROBE_TIMEOUT,
            allow_redirects=True,
        )

        code = response.status_code

        if code >= 400:
            status = "blocked"
            error = f"HTTP {code} - {blocked_reason}"
        else:
            status = "blocked"
            error = (
                f"HTTP {code} (no job data - anti-bot/JS shell) "
                f"- {blocked_reason}"
            )

    except requests.RequestException as exc:
        status = "blocked"
        error = f"{blocked_reason} - {exc}"

    return {
        "provider": provider,
        "status": status,
        "count": 0,
        "error": error,
        "jobs": [],
    }


def normalize_common(
    source,
    *,
    source_job_id="",
    title="",
    company="",
    location="",
    remote=None,
    url="",
    description="",
    date_posted="",
    employment_type="",
    experience="",
    salary="",
    skills=None,
    search_query="",
    search_location="",
    raw=None,
):
    """Normalize one raw job into the common job schema."""
    url = str(url or "").strip()
    source_job_id = str(source_job_id or "").strip()

    job = {
        "source": source,
        "source_job_id": source_job_id or url,
        "title": str(title or "").strip(),
        "company": str(company or "").strip(),
        "location": str(location or "").strip(),
        "remote": bool(remote) if remote is not None else None,
        "url": url,
        "job_url": url,
        "description": str(description or "").strip(),
        "date_posted": str(date_posted or ""),
        "employment_type": str(employment_type or ""),
        "experience": str(experience or ""),
        "salary": str(salary or ""),
        "skills": list(skills or []),
        "search_query": str(search_query or ""),
        "search_location": str(search_location or ""),
        "raw_source_data": dict(raw or {}),
    }

    return job