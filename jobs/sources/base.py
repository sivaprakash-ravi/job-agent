"""Shared helpers, search-term building and the common job schema.

Every source adapter normalizes its raw payloads into the common
schema defined by :func:`normalize_common` and returns a result dict::

    {
        "provider": "name",
        "status": "ok" | "blocked" | "unavailable" | "error" | "zero_results",
        "count": <int>,
        "error": "<description>",
        "jobs": [ <common schema jobs> ],
    }

profile.py remains the single source of truth for roles, skills,
locations and preferences.
"""

import hashlib
import re
from datetime import datetime, timezone
from html import unescape

import requests

from profile import LOCATIONS, SKILLS, TARGET_ROLES


PROVIDER_STATUS = {
    "ok": "ok",
    "blocked": "blocked",
    "unavailable": "unavailable",
    "error": "error",
    "zero_results": "zero_results",
    "unsupported": "unsupported",
}


def now_utc_iso():
    """Return the current UTC time as an ISO string."""
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
    )


def content_hash(value):
    """Deterministic short hash of job content for similarity checks."""
    return hashlib.sha1(
        str(value or "").encode("utf-8", errors="ignore")
    ).hexdigest()[:16]


REMOTE_TOKENS = (
    "remote",
    "anywhere",
    "work from home",
    "wfh",
    "fully remote",
    "100% remote",
)


def detect_remote(*texts):
    """Return True when any supplied text clearly indicates remote work."""
    for text in texts:
        lower = str(text or "").lower()

        if any(token in lower for token in REMOTE_TOKENS):
            return True

    return False


def html_to_text(value, max_chars=None):
    """Convert an HTML fragment into readable plain text."""
    text = unescape(str(value or ""))

    text = re.sub(
        r"<(script|style)\b[^>]*>.*?</\1>",
        " ",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )

    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)

    text = re.sub(
        r"</(?:p|div|li|section|article|h[1-6])>",
        "\n",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(r"<[^>]+>", " ", text)

    text = re.sub(r"[\r\n]+", " ", text)
    text = re.sub(r"[ \t]+", " ", text)

    text = unescape(text).strip()

    if max_chars and len(text) > max_chars:
        text = text[:max_chars]

    return text


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
    """Build focused search queries balanced across career families.

    Queries are generated from profile.JOB_FAMILY_QUERY_TERMS and
    interleaved round-robin across the user's priority tiers (P1
    support, P2 QA, P3 dev/DevOps), so no single family can dominate
    the query budget. Generic skill / synonym / legacy terms are
    appended afterwards for recall. Never one giant Boolean query.
    """
    from profile import (
        JOB_FAMILY_PRIORITY,
        JOB_FAMILY_QUERY_TERMS,
    )

    terms_by_priority = {1: [], 2: [], 3: []}

    for family, terms in JOB_FAMILY_QUERY_TERMS.items():
        priority = JOB_FAMILY_PRIORITY.get(
            family, 3
        )
        terms_by_priority[priority].extend(terms)

    pools = {
        1: list(
            dict.fromkeys(
                term.strip()
                for term in terms_by_priority[1]
                if term.strip()
            )
        ),
        2: list(
            dict.fromkeys(
                term.strip()
                for term in terms_by_priority[2]
                if term.strip()
            )
        ),
        3: list(
            dict.fromkeys(
                term.strip()
                for term in terms_by_priority[3]
                if term.strip()
            )
        ),
    }

    family_queries = []
    index = 0

    while any(
        index < len(pool)
        for pool in pools.values()
    ):
        for priority in (
            1,
            2,
            3,
        ):
            if index < len(
                pools[priority]
            ):
                family_queries.append(
                    pools[priority][index]
                )

        index += 1

    family_set = set(
        query.lower()
        for query in family_queries
    )

    # Generic recall tail: skills, synonyms and the legacy broad list,
    # minus terms already covered by the family pools.
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

    tail = [
        term.strip()
        for term in (
            BROAD_QUERIES
            + TARGET_ROLES
            + ROLE_SYNONYMS
            + skill_queries
        )
        if (
            term.strip()
            and term.strip().lower()
            not in family_set
        )
    ]

    queries = list(
        dict.fromkeys(
            family_queries + tail
        )
    )

    if limit is not None and limit > 0:
        return queries[:limit]

    return queries


BROAD_QUERIES = [
    "DevOps",
    "DevOps Engineer",
    "Cloud Engineer",
    "Cloud Support",
    "Cloud Operations",
    "SRE",
    "Site Reliability",
    "Infrastructure",
    "Infrastructure Engineer",
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


ROLE_SYNONYMS = [
    "site reliability engineer",
    "sre engineer",
    "devops",
    "devops engineer",
    "cloud infrastructure",
    "cloud infrastructure engineer",
    "infrastructure support",
    "infrastructure support engineer",
    "cloud reliability",
    "platform engineer",
    "platform operations",
    "sre",
    "reliability engineer",
    "cloud operations engineer",
    "application support engineer",
    "production support engineer",
    "tech support engineer",
    "technical operations",
    "system operations",
    "monitoring engineer",
    "observability",
    "incident management",
    "qa tester",
    "qa analyst",
    "quality analyst",
    "manual tester",
    "test analyst",
    "software tester",
]


# ============================================================
# QUERY FAMILY TRACKING
# ============================================================

def _build_search_query_families():
    """Map each configured search term to its career family."""
    from profile import JOB_FAMILY_QUERY_TERMS

    mapping = {}

    for family, terms in JOB_FAMILY_QUERY_TERMS.items():
        for term in terms:
            key = term.strip().lower()

            if key and key not in mapping:
                mapping[key] = family

    return mapping


SEARCH_QUERY_FAMILIES = _build_search_query_families()


def query_family_for(query):
    """Career family behind a search query, or 'generic'."""
    return SEARCH_QUERY_FAMILIES.get(
        str(query or "").strip().lower(),
        "generic",
    )


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
    apply_url="",
    description="",
    requirements="",
    responsibilities="",
    date_posted="",
    posted_at="",
    employment_type="",
    experience="",
    experience_min="",
    experience_max="",
    salary="",
    skills=None,
    search_query="",
    search_location="",
    json_ld=None,
    raw=None,
):
    """Normalize one raw job into the common job schema."""
    url = str(url or "").strip()
    apply_url = str(apply_url or "").strip() or url
    source_job_id = str(source_job_id or "").strip()
    location = str(location or "").strip()

    job = {
        "source": source,
        "source_job_id": source_job_id or url,
        "title": str(title or "").strip(),
        "company": str(company or "").strip(),
        "location": location,
        "remote": bool(remote) if remote is not None else None,
        "url": url,
        "job_url": url,
        "apply_url": apply_url,
        "description": str(description or "").strip(),
        "requirements": str(requirements or "").strip(),
        "responsibilities": str(responsibilities or "").strip(),
        "date_posted": str(date_posted or ""),
        "posted_at": str(posted_at or "") or str(date_posted or ""),
        "employment_type": str(employment_type or ""),
        "experience": str(experience or ""),
        "experience_min": str(experience_min or ""),
        "experience_max": str(experience_max or ""),
        "salary": str(salary or ""),
        "skills": list(skills or []),
        "search_query": str(search_query or ""),
        "search_location": str(search_location or ""),
        "discovered_at": now_utc_iso(),
        "content_hash": content_hash(
            f"{url}|{title}|{company}|{description}"
        ),
        "normalized_identity": "",
        "raw_source_data": dict(raw or {}),
    }

    if json_ld is not None:
        job["json_ld"] = json_ld

    try:
        from canonical import job_identity

        identity = job_identity(job)

        if identity:
            job["normalized_identity"] = identity
    except Exception:
        job["normalized_identity"] = ""

    return job