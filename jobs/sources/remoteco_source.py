"""Remote.co adapter.

The site times out for anonymous requests (no structured public
API). We probe once and report the outcome; we do not bypass
protections.
"""

from sources.base import probe_result


PROBE_URL = "https://remote.co/remote-jobs/"


def run(search_queries, locations=None):
    return probe_result(
        "remoteco",
        PROBE_URL,
        "Remote.co does not respond to anonymous requests (timeout)",
    )