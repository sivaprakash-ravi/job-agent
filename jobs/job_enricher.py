"""Fetch and enrich job postings before final filtering."""

import json
import re
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from html import unescape


MAX_WORKERS = 8
REQUEST_TIMEOUT = 12


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,"
        "application/xml;q=0.9,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def clean_html(html):
    """Convert HTML into readable plain text."""

    html = unescape(html)

    # Remove scripts/styles.
    html = re.sub(
        r"<script\b[^>]*>.*?</script>",
        " ",
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )

    html = re.sub(
        r"<style\b[^>]*>.*?</style>",
        " ",
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )

    # Preserve useful separators.
    html = re.sub(
        r"<br\s*/?>",
        "\n",
        html,
        flags=re.IGNORECASE,
    )

    html = re.sub(
        r"</(?:p|div|li|section|article|h[1-6])>",
        "\n",
        html,
        flags=re.IGNORECASE,
    )

    # Remove remaining tags.
    html = re.sub(
        r"<[^>]+>",
        " ",
        html,
    )

    # Decode common entities again.
    html = unescape(html)

    # Normalize whitespace.
    lines = []

    for line in html.splitlines():

        line = re.sub(
            r"\s+",
            " ",
            line,
        ).strip()

        if line:
            lines.append(line)

    return "\n".join(lines)


def extract_json_ld(html):
    """Extract JobPosting JSON-LD objects."""

    results = []

    patterns = re.findall(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>'
        r"(.*?)"
        r"</script>",
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )

    for raw in patterns:

        raw = raw.strip()

        try:
            data = json.loads(raw)

        except Exception:
            continue

        if isinstance(data, dict):
            results.append(data)

        elif isinstance(data, list):
            results.extend(
                item
                for item in data
                if isinstance(item, dict)
            )

    return results


def json_ld_text(objects):
    """Convert JSON-LD job information into searchable text."""

    parts = []

    for obj in objects:

        for key, value in obj.items():

            if isinstance(value, (dict, list)):
                try:
                    value = json.dumps(
                        value,
                        ensure_ascii=False,
                    )
                except Exception:
                    value = str(value)

            parts.append(
                f"{key}: {value}"
            )

    return "\n".join(parts)


def fetch_job_page(job):
    """
    Fetch the public job URL and extract all available text.

    Failure does NOT mean the job is rejected.
    It means verification may be incomplete.
    """

    url = (
        job.get("url")
        or job.get("job_url")
        or ""
    )

    result = {
        "success": False,
        "status": "UNVERIFIED",
        "url": url,
        "page_text": "",
        "json_ld": [],
        "error": "",
    }

    if not url:
        result["error"] = "No job URL"
        return result

    request = urllib.request.Request(
        url,
        headers=HEADERS,
    )

    try:

        with urllib.request.urlopen(
            request,
            timeout=REQUEST_TIMEOUT,
        ) as response:

            content_type = (
                response.headers.get(
                    "Content-Type",
                    "",
                )
            )

            raw = response.read()

            # Only decode HTML/text responses.
            if (
                "html" not in content_type.lower()
                and "text" not in content_type.lower()
            ):
                result["error"] = (
                    "Job URL did not return HTML/text"
                )

                return result

            html = raw.decode(
                "utf-8",
                errors="ignore",
            )

            page_text = clean_html(
                html
            )

            json_ld = extract_json_ld(
                html
            )

            result["success"] = True
            result["status"] = "VERIFIED_SOURCE"
            result["page_text"] = page_text
            result["json_ld"] = json_ld
            result["json_ld_text"] = (
                json_ld_text(json_ld)
            )

            return result

    except urllib.error.HTTPError as error:

        result["error"] = (
            f"HTTP {error.code}"
        )

    except urllib.error.URLError as error:

        result["error"] = (
            f"URL error: {error.reason}"
        )

    except Exception as error:

        result["error"] = str(error)

    return result


def enrich_job(job):
    """Merge fetched job-page information into the original job."""

    enriched = dict(job)

    page = fetch_job_page(
        job
    )

    enriched["detail_verification"] = {
        "status": page.get(
            "status",
            "UNVERIFIED",
        ),
        "success": page.get(
            "success",
            False,
        ),
        "error": page.get(
            "error",
            "",
        ),
    }

    if page.get("page_text"):

        enriched[
            "full_job_page_text"
        ] = page["page_text"]

    if page.get("json_ld"):

        enriched[
            "job_page_json_ld"
        ] = page["json_ld"]

    if page.get("json_ld_text"):

        enriched[
            "job_page_json_ld_text"
        ] = page["json_ld_text"]

    return enriched


def enrich_jobs(jobs):
    """
    Enrich jobs concurrently.

    The original API/JobSpy metadata is always preserved.
    """

    if not jobs:
        return []

    results = [None] * len(jobs)

    with ThreadPoolExecutor(
        max_workers=MAX_WORKERS
    ) as executor:

        future_map = {
            executor.submit(
                enrich_job,
                job,
            ): index
            for index, job in enumerate(jobs)
        }

        for future in as_completed(
            future_map
        ):

            index = future_map[
                future
            ]

            try:

                results[index] = (
                    future.result()
                )

            except Exception as error:

                fallback = dict(
                    jobs[index]
                )

                fallback[
                    "detail_verification"
                ] = {
                    "status": "UNVERIFIED",
                    "success": False,
                    "error": str(error),
                }

                results[index] = fallback

    return [
        job
        for job in results
        if job is not None
    ]