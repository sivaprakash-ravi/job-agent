"""We Work Remotely adapter.

Uses the public We Work Remotely RSS feeds:
https://weworkremotely.com/categories/*.rss
"""

import xml.etree.ElementTree as ElementTree

from sources.base import fetch_text, normalize_common


RSS_CATEGORIES = {
    "remote-full-stack-programming-jobs": "Full-Stack Programming",
    "remote-programming-jobs": "Programming",
    "remote-devops-sysadmin-jobs": "DevOps / Sysadmin",
    "remote-customer-support-jobs": "Customer Support",
}

MAX_JOBS = 300


def run(search_queries, locations=None):
    """Collect remote jobs from We Work Remotely RSS feeds."""
    result = {
        "provider": "weworkremotely",
        "status": "ok",
        "count": 0,
        "error": "",
        "jobs": [],
    }

    raw_items = []

    for category in RSS_CATEGORIES:
        url = f"https://weworkremotely.com/categories/{category}.rss"

        try:
            xml_text = fetch_text(url, max_bytes=3 * 1024 * 1024)
        except Exception as error:
            result["error"] = (
                f"{result['error']} ; {category}: {error}"
                if result["error"]
                else f"{category}: {error}"
            )
            continue

        try:
            root = ElementTree.fromstring(xml_text)
        except ElementTree.ParseError:
            result["error"] = (
                f"{result['error']} ; {category}: RSS parse failed"
                if result["error"]
                else f"{category}: RSS parse failed"
            )
            continue

        for item in root.iter("item"):
            raw_items.append(item)

    jobs = []

    for item in raw_items:
        title = text_of(item, "title")

        if not title:
            continue

        company, role_title = split_company_title(title)

        job = normalize_common(
            source="weworkremotely",
            source_job_id=text_of(item, "guid") or text_of(item, "link"),
            title=role_title or title,
            company=company,
            location="Remote",
            remote=True,
            url=text_of(item, "link"),
            description=text_of(item, "description"),
            date_posted=text_of(item, "pubDate"),
            employment_type="",
            skills=[],
            search_query="",
            search_location="Remote",
            raw={
                "category": text_of(item, "category"),
            },
        )

        if job["url"]:
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


def text_of(element, tag):
    """Return the text of a child RSS element."""
    child = element.find(tag)

    if child is None or child.text is None:
        return ""

    return " ".join(child.text.split())


def split_company_title(title):
    """Extract company and role from a "Company: Role" title.

    We Work Remotely titles follow the
    ``Company Name: Role Title`` convention.
    """
    if ":" not in title:
        return "", title

    company, _, role = title.partition(":")

    company = company.strip()

    role = role.strip()

    if not company or not role:
        return "", title

    return company, role