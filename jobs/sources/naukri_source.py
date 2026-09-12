"""Naukri direct-web adapter.

Direct Naukri search requires a session token and captcha controls;
the public jobapi requires App Id/SystemId headers (HTTP 400). The
Naukri provider is instead covered through JobSpy. We probe the
direct web endpoint once and report the outcome.
"""

from sources.base import probe_result


PROBE_URL = "https://www.naukri.com/devops-engineer-jobs"


def run(search_queries, locations=None):
    return probe_result(
        "naukri",
        PROBE_URL,
        "Direct Naukri scraping requires session token/captcha (covered via JobSpy)",
    )