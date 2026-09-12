"""Foundit (Monster India) adapter.

The public search endpoints require bot protection / login
(HTTP 403). We probe once and report the outcome; we do not
bypass protections.
"""

import urllib.parse

from sources.base import probe_result


PROBE_URL = (
    "https://www.foundit.in/search/?query="
    + urllib.parse.quote("DevOps Engineer")
)


def run(search_queries, locations=None):
    return probe_result(
        "foundit",
        PROBE_URL,
        "Foundit blocks anonymous search requests (HTTP 403)",
    )