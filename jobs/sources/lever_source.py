"""Lever ATS adapter.

The public Lever posting API/board endpoints are currently
unavailable (HTTP 404 across known boards). We probe once and
report the outcome; we do not bypass access controls.
"""

from sources.base import probe_result


PROBE_URL = "https://api.lever.co/v0/postings/lever?mode=json"


def run(search_queries, locations=None):
    return probe_result(
        "lever",
        PROBE_URL,
        "Lever public postings API unavailable (HTTP 404)",
    )