"""TimesJobs adapter.

The site refuses anonymous connections (TLS/connection errors) and
requires login for jobs. We probe once and report the outcome; we
do not bypass protections.
"""

from sources.base import probe_result


PROBE_URL = "https://www.timesjobs.com/jobsearch/job-search-category.html"


def run(search_queries, locations=None):
    return probe_result(
        "timesjobs",
        PROBE_URL,
        "TimesJobs rejects anonymous connections (TLS/connection error)",
    )