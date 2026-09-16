"""Public source discovery for career pages / ATS boards (V1.2).

Purpose is additive metadata ONLY: it may surface candidate domains
(for a human to review later) and never changes what the pipeline
fetches. Discovery is best-effort:

- Uses ``ddgs`` only if it is installed; otherwise it reports
  ``source_discovery="unavailable"`` and the pipeline continues.
- Never bypasses CAPTCHA / Cloudflare / login / robots.txt.
- Fetches only public pages with a normal browser User-Agent.
- Executes NO discovered code and treats every candidate page / JD as
  untrusted plain text.

Candidates land in a registry record:
    {domain, url, detected_ats, evidence, first_seen, status,
     human_approval_required}
``human_approval_required`` is always True - a discovered domain is
NEVER silently added as a provider. Only known-safe ATS signatures are
auto-classified into ``detected_ats``; everything else stays
``detected_ats=None`` pending human judgement.
"""

import re
from datetime import datetime, timezone

import ai_config

# Known ATS URL signatures. Each entry is a list of regex patterns
# matched against a candidate page URL (and title when present).
ATS_SIGNATURES = {
    "greenhouse": [
        r"boards\.greenhouse\.io",
        r"job-boards\.greenhouse\.io",
    ],
    "lever": [
        r"jobs\.lever\.co",
        r"lever\.co/[^/]+(?:/jobs|/postings)",
    ],
    "ashby": [
        r"jobs\.ashbyhq\.com",
        r"ashbyhq\.com",
    ],
    "workable": [
        r"jobs\.workable\.com",
        r"apply\.workable\.com",
        r"jobs\.workable\.\w+",
    ],
    "smartrecruiters": [
        r"jobs\.smartrecruiters\.com",
        r"smartrecruiters\.com/[^/]+",
    ],
    "recruitee": [
        r"recruitee\.com",
        r"\.recruitee\.com",
    ],
    "teamtailor": [
        r"teamtailor\.com",
        r"\.teamtailor\.com",
    ],
    "personio": [
        r"jobs\.personio\.de",
        r"jobs\.personio\.com",
        r"personio\.de/jobs",
        r"personio\.com/jobs",
    ],
}

# Substrings that indicate a real careers page vs a generic scrape.
CAREERS_HINTS = (
    "careers",
    "jobs",
    "join-us",
    "join us",
    "working-at",
    "work-with-us",
    "openings",
    "vacancies",
)

FEED_CONFIRM_HINTS = (
    "greenhouse.io",
    "lever.co",
    "ashbyhq.com",
    "workable.com",
    "smartrecruiters.com",
    "recruitee.com",
    "teamtailor.com",
    "personio",
)


def detect_ats_type(url, text=None):
    """Return the ATS vendor behind a URL, or None."""
    haystack = str(url or "").lower()

    if text:
        haystack = f"{haystack} {str(text).lower()}"

    for ats, patterns in ATS_SIGNATURES.items():
        for pattern in patterns:
            if re.search(pattern, haystack):
                return ats

    return None


def _looks_like_careers_url(url):
    return any(
        hint in str(url or "").lower()
        for hint in CAREERS_HINTS
    )


def _candidate_record(url, detected_ats, evidence, source_query):
    return {
        "domain": str(url or ""),
        "url": str(url or ""),
        "detected_ats": detected_ats,
        "evidence": evidence,
        "first_seen": (
            datetime.now(timezone.utc)
            .isoformat(timespec="seconds")
        ),
        "source_query": source_query,
        "status": "pending_review",
        "human_approval_required": True,
    }


def _load_ddgs():
    """Try to import the optional ddgs search helper.

    Returns ``(DDGS_or_None, error_message)``.
    """
    try:
        from ddgs import DDGS  # noqa: E402  (optional dependency)

        return DDGS, None
    except Exception as exc:  # pragma: no cover - environment-dependent
        return None, str(exc)


def discover_sources(
    search_queries,
    budget=None,
    max_results_per_query=2,
):
    """Best-effort public-source discovery.

    Returns ``(status, candidates, error)``:

    - ``status`` in {"available", "unavailable", "error"}
    - ``candidates`` a list of registry records (may be empty)
    - ``error`` a human-readable note

    ``ddgs`` performs the web search. When it is not installed the
    result is ``("unavailable", [], "ddgs not installed")`` and the
    caller must continue the pipeline unchanged.
    """
    if budget is None:
        budget = ai_config.MAX_SOURCE_LOOKUPS

    search_queries = [
        str(query).strip()
        for query in (search_queries or [])
        if str(query or "").strip()
    ]

    if not search_queries or budget <= 0:
        return "available", [], "no queries or budget"

    DDGS, import_error = _load_ddgs()

    if DDGS is None:
        return (
            "unavailable",
            [],
            f"ddgs not installed: {import_error}",
        )

    candidates = []
    seen_domains = set()
    queries_budget = budget

    try:
        with DDGS() as ddgs:
            for query in search_queries:
                if len(candidates) >= queries_budget:
                    break

                for result in ddgs.text(
                    query,
                    max_results=max_results_per_query,
                ):
                    url = str(result.get("href") or "").strip()

                    if _looks_like_careers_url(url) or detect_ats_type(url):
                        domain = url

                        if domain in seen_domains:
                            continue

                        seen_domains.add(domain)

                        text = str(
                            result.get("body")
                            or result.get("title")
                            or ""
                        )

                        candidates.append(
                            _candidate_record(
                                url=url,
                                detected_ats=detect_ats_type(url, text),
                                evidence=(
                                    str(result.get("title") or "")[:200]
                                ),
                                source_query=query,
                            )
                        )

                        if len(candidates) >= queries_budget:
                            break

    except Exception as exc:  # network / parse errors are non-fatal
        return (
            "error",
            candidates,
            f"ddgs lookup failed midway: {exc}",
        )

    return "available", candidates, ""


def classify_candidates(candidates):
    """Group candidates for the source-discovery report.

    ATS-detected candidates are flagged (auto-classified, still human
    approval required); everything else stays pending review.
    """
    ats_detected = [
        item.get("detected_ats")
        for item in candidates
        if item.get("detected_ats")
    ]

    from collections import Counter

    return {
        "total_candidates": len(candidates),
        "ats_detected": dict(Counter(ats_detected)),
        "approved": [],
        "rejected": [],
        "pending_review": [
            {
                "url": item.get("url"),
                "detected_ats": item.get("detected_ats"),
                "evidence": item.get("evidence"),
                "source_query": item.get("source_query"),
                "human_approval_required": item.get(
                    "human_approval_required"
                ),
            }
            for item in candidates
        ],
    }