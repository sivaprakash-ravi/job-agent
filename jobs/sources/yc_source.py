"""Y Combinator Work at a Startup adapter.

The public site is protected by Cloudflare / anti-bot controls
(HTTP 406). We probe it once and report the outcome; we do not
bypass protections.
"""

from sources.base import probe_result


PROBE_URL = "https://www.workatastartup.com/jobs"


def run(search_queries, locations=None):
    return probe_result(
        "yc",
        PROBE_URL,
        "Work at a Startup is behind Cloudflare/anti-bot controls",
    )