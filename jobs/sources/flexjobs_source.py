"""FlexJobs adapter.

FlexJobs is a paid subscription service behind login and it times
out for anonymous requests. We probe once and report the outcome;
we do not bypass access controls.
"""

from sources.base import probe_result


PROBE_URL = "https://www.flexjobs.com/search?searchterm=devops"


def run(search_queries, locations=None):
    return probe_result(
        "flexjobs",
        PROBE_URL,
        "FlexJobs is a paid service behind login (timeout)",
    )