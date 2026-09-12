"""Canonical normalization and global cross-provider deduplication.

Deduplication priority:

1. canonical job URL
2. source_job_id
3. normalized company + normalized title + normalized location

The same underlying job discovered on LinkedIn, Indeed, Google or
any other provider must collapse into one record.
"""

import hashlib
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


MIN_CONTENT_DEDUPE_CHARS = 250


def content_dedupe_key(job):
    """Return a content-based cross-provider dedupe key.

    Only engages when the listing carries a rich description so two
    genuinely distinct jobs are never merged on vague boilerplate.
    """
    title = normalize_title(
        job.get("title")
    )

    if not title:
        return None

    description = str(
        job.get("description")
        or job.get("job_description")
        or ""
    ).strip()

    if len(description) < MIN_CONTENT_DEDUPE_CHARS:
        return None

    words = " ".join(
        word
        for word in re.findall(
            r"[a-z0-9]+",
            normalize_text(description),
        )
        if len(word) > 2
    )

    digest = hashlib.sha1(
        words.encode(
            "utf-8",
            errors="ignore",
        )
    ).hexdigest()[:24]

    return f"content:{title}|{digest}"


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

    Two layers:

    1. stable identity (url -> provider id -> company+title+location)
    2. content hash for cross-provider duplicates whose URLs differ
       but whose title and rich description match
    """
    unique = []
    seen_identity = set()
    seen_content = set()

    def _record_duplicate(source, identity, content_key):
        duplicates = []

        for kept in unique:
            kept_identity = job_identity(kept)
            kept_content = content_dedupe_key(kept)

            if (
                identity
                and kept_identity == identity
            ) or (
                content_key
                and kept_content == content_key
            ):
                kept_duplicates = set(
                    kept.get("duplicate_sources") or []
                )
                kept_duplicates.add(source)
                kept["duplicate_sources"] = sorted(
                    kept_duplicates
                )
                duplicates.append(kept)
                break

        return duplicates

    for job in jobs:
        identity = job_identity(job)
        content_key = content_dedupe_key(job)
        source = str(job.get("source") or "unknown")

        if not identity and not content_key:
            continue

        if identity and identity in seen_identity:
            _record_duplicate(source, identity, None)
            continue

        if (
            content_key
            and content_key in seen_content
        ):
            _record_duplicate(source, None, content_key)
            continue

        if identity:
            seen_identity.add(identity)

        if content_key:
            seen_content.add(content_key)

        if "duplicate_sources" not in job:
            job["duplicate_sources"] = []

        unique.append(job)

    return unique