"""Generic RSS/Atom job-feed adapter.

Used for curated feeds such as EuroRemote and Python.org jobs.
Parses standard RSS 2.0 / Atom with the standard library only so
it stays safe in GitHub Actions and offline environments.
"""

import re
from datetime import datetime
from email.utils import parsedate_to_datetime
from xml.etree import ElementTree

import requests

from sources.base import (
    detect_remote,
    html_to_text,
    normalize_common,
)


FEEDS = {
    "euroremote": {
        "url": "https://euroremote.eu/rss",
        "name": "Euro Remote",
        "remote": True,
        "max": 300,
    },
    "pythondotorg": {
        "url": "https://www.python.org/jobs/feed/rss/",
        "name": "Python.org Jobs",
        "remote": None,
        "max": 200,
    },
}


def _localname(tag):
    """Strip XML namespace prefix from an element tag."""
    if "}" in tag:
        return tag.rsplit("}", 1)[1]

    return tag


def _text(element, keys, namespaces=None):
    """Find the first matching child text under an element."""
    if element is None:
        return ""

    for key in keys:
        candidate = element.find(key)

        if candidate is not None and candidate.text:
            return candidate.text.strip()

    if namespaces:
        for key in keys:
            local = key.rsplit("}", 1)[-1]

            for child in element:
                if _localname(child.tag) == local and child.text:
                    return child.text.strip()

    return ""


def _parse_date(value):
    """Normalize an RFC 2822 / ISO date to a short compact string."""
    value = str(value or "").strip()

    if not value:
        return ""

    for fmt in (
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S %Z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ):
        try:
            return datetime.strptime(
                value,
                fmt,
            ).strftime("%Y-%m-%d")
        except ValueError:
            continue

    try:
        parsed = parsedate_to_datetime(value)

        return parsed.strftime("%Y-%m-%d")
    except Exception:
        return value[:16]


def _fetch_feed(url):
    """Fetch and parse an RSS/Atom feed into a list of entries."""
    response = requests.get(
        url,
        timeout=30,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; job-agent-research/2.0)"
        },
    )
    response.raise_for_status()

    root = ElementTree.fromstring(response.content)

    channel = root.find("channel")

    items = list(
        root.findall("channel/item") or root.findall(".//item")
    )

    if not items and channel is None:
        items = list(root.findall(".//{*}entry")) or list(
            root.iter("{http://www.w3.org/2005/Atom}entry")
        )

    return items, channel


def _entry_fields(item):
    """Extract title/link/description/date/author from any entry."""
    title = _text(item, ["title"])
    link = (
        _text(item, ["link", "{http://www.w3.org/2005/Atom}link"])
        or (item.get("{http://www.w3.org/2005/Atom}href") if item is not None else "")
    )

    if item is not None and hasattr(item, "attrib"):
        if not link and "href" in item.attrib:
            link = item.attrib["href"]

    description = _text(item, ["description", "summary", "content"])

    if not description:
        description = _text(item, ["encoded", "{http://purl.org/rss/1.0/modules/content/}encoded"])

    date = _text(item, ["pubDate", "published", "updated", "{http://www.w3.org/2005/Atom}updated"])

    author = _text(item, ["dc:creator", "author", "company"])

    if not author:
        author = _text(item, ["name"], namespaces=True)

    return title, link, description, date, author


def run(search_queries, locations=None):
    """Collect jobs from every configured RSS feed."""
    result = {
        "provider": "rss",
        "status": "ok",
        "count": 0,
        "error": "",
        "jobs": [],
    }

    target_keys = None
    jobs, errors = _collect_feeds(target_keys)

    seen = set()
    unique = []

    for job in jobs:
        key = job["url"] or job["source_job_id"]

        if not key or key in seen:
            continue

        seen.add(key)
        unique.append(job)

    result["jobs"] = unique
    result["count"] = len(result["jobs"])

    if errors:
        result["error"] = "; ".join(errors[:3])

    return result


def run_euroremote(search_queries, locations=None):
    """Collect only the EuroRemote feed."""
    return _run_feed(["euroremote"])


def run_pythondotorg(search_queries, locations=None):
    """Collect only the Python.org jobs feed."""
    return _run_feed(["pythondotorg"])


def _run_feed(keys):
    """Collect one specific feed into a provider result."""
    jobs, errors = _collect_feeds(keys)

    result = {
        "provider": keys[0],
        "status": "ok",
        "count": 0,
        "error": "",
        "jobs": jobs[: FEEDS[keys[0]].get("max", 300)],
    }
    result["count"] = len(result["jobs"])

    if errors:
        result["error"] = "; ".join(errors[:3])

    return result


def _collect_feeds(target_keys=None):
    """Fetch configured (or select) feeds and normalize entries."""
    jobs = []
    errors = []

    for key, config in FEEDS.items():
        if target_keys is not None and key not in target_keys:
            continue

        try:
            items, _channel = _fetch_feed(config["url"])
        except Exception as error:
            errors.append(f"{key}: {error}")
            continue

        default_remote = config.get("remote")

        for item in items:
            title, link, description, date, author = _entry_fields(item)

            title = str(title or "").strip()

            if not title or not link:
                continue

            text = html_to_text(description)
            remote = detect_remote(text)

            if default_remote is True:
                remote = True

            location = "Remote" if remote else ""

            if not author:
                author = str(config.get("name") or key)

            jobs.append(
                normalize_common(
                    source=key,
                    source_job_id=link,
                    title=title,
                    company=author,
                    location=location,
                    remote=True if remote else None,
                    url=link,
                    description=text,
                    date_posted=_parse_date(date),
                    posted_at=_parse_date(date),
                    employment_type="",
                    search_query="RSS feed",
                    search_location="Remote" if remote else "",
                    json_ld=None,
                    raw={"feed": key},
                )
            )

    return jobs, errors