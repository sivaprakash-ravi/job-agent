"""Canonical normalization and global cross-provider deduplication.

Deduplication priority:

1. canonical job URL
2. source_job_id
3. normalized company + normalized title + normalized location

The same underlying job discovered on LinkedIn, Indeed, Google or
any other provider must collapse into one record.
"""

import re
import urllib.parse

TRACKING_QUERY_KEYS = frozenset(
    [
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_term",
        "utm_content",
        "fbclid",
        "gclid",
        "mc_cid",
        "mc_eid",
        "igshid",
    ]
)


def normalize_url(url):
    """Canonicalize a job URL for duplicate detection."""
    value = str(url or "").strip().lower()

    if not value:
        return ""

    try:
        parsed = urllib.parse.urlsplit(value)
    except ValueError:
        return value.rstrip("/")

    query = urllib.parse.parse_qsl(parsed.query)

    kept = [
        (key, val)
        for key, val in query
        if key.lower() not in TRACKING_QUERY_KEYS
    ]

    rebuilt_query = urllib.parse.urlencode(kept)

    netloc = parsed.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[len("www."):]

    rebuilt = urllib.parse.urlunsplit(
        (parsed.scheme, netloc, parsed.path, rebuilt_query, "")
    )

    return rebuilt.rstrip("/")


def normalize_text(value):
    """Normalize arbitrary text for identity keys."""
    return " ".join(str(value or "").lower().split())


def normalize_company(value):
    """Normalize company names, dropping legal suffixes."""
    text = normalize_text(value)

    text = re.sub(
        r"\b(private limited|pvt ltd|pvt ltd\.|ltd|limited|inc)\.?\b",
        " ",
        text,
    )

    return re.sub(r"\s+", " ", text).strip()


def normalize_title(value):
    """Normalize job titles."""
    text = normalize_text(value)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def normalize_location(value):
    """Normalize location text for identity keys."""
    text = normalize_text(value)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def canonical_url_key(job):
    """Return the canonical URL key, if any."""
    url = normalize_url(
        job.get("url")
        or job.get("job_url")
    )

    if url:
        return f"url:{url}"

    return None


def source_job_id_key(job):
    """Return the provider id key, if any."""
    source = str(job.get("source") or "").strip().lower()
    source_job_id = str(job.get("source_job_id") or "").strip()

    if not source or not source_job_id:
        return None

    return f"id:{source}:{source_job_id}"


def name_key(job):
    """Return the company+title+location key, if any."""
    company = normalize_company(
        job.get("company")
        or job.get("company_name")
    )

    title = normalize_title(
        job.get("title")
    )

    location = normalize_location(
        job.get("location")
        or job.get("search_location")
    )

    if not company and not title:
        return None

    return f"job:{company}|{title}|{location}"


def job_identity(job):
    """Return a single stable identity string for a job.

    URL first, then provider id, then company+title+location.
    """
    for candidate in (
        canonical_url_key,
        source_job_id_key,
        name_key,
    ):
        key = candidate(job)

        if key:
            return key

    return None


def deduplicate_jobs(jobs):
    """Globally deduplicate jobs across all providers.

    Preserves the first occurrence and records which other sources
    reported the same underlying job in ``duplicate_sources``.
    """
    unique = []
    seen = set()

    for job in jobs:
        identity = job_identity(job)

        if not identity:
            continue

        if identity in seen:
            duplicates = job.get("duplicate_sources") or []
            owner = job.get("source") or "unknown"

            if owner not in duplicates:
                duplicates.append(owner)

            for kept in unique:
                kept_identity = job_identity(kept)

                if kept_identity == identity:
                    kept_duplicates = set(
                        kept.get("duplicate_sources") or []
                    )
                    kept_duplicates.add(owner)
                    kept["duplicate_sources"] = sorted(kept_duplicates)
                    break

            continue

        seen.add(identity)

        if "duplicate_sources" not in job:
            job["duplicate_sources"] = []

        unique.append(job)

    return unique