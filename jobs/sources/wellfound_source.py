"""Wellfound adapter.

The jobs pages require a Cloudflare Turnstile challenge and the
data is client-side rendered. We probe once and report the outcome;
we do not bypass protections.
"""

from sources.base import probe_result


PROBE_URL = "https://wellfound.com/role/r/devops-engineer"


def run(search_queries, locations=None):
    return probe_result(
        "wellfound",
        PROBE_URL,
        "Wellfound served Cloudflare Turnstile challenge",
    )