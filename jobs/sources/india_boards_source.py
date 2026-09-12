"""India job-board adapters that require login or JS rendering.

Each provider is probed once with a polite request and reports the
honest outcome. None of these providers can be scraped reliably
without authentication or bypassing protections.

Covered providers:
- Instahyre
- Cutshort
- Unstop
- Shine
- Freshersworld
"""

from sources.base import probe_result


PROVIDERS = [
    (
        "instahyre",
        "https://www.instahyre.com/jobs/",
        "Instahyre is a JS-only SPA with no public job API",
    ),
    (
        "cutshort",
        "https://cutshort.io/jobs",
        "Cutshort requires auth; no public job API",
    ),
    (
        "unstop",
        "https://unstop.com/jobs",
        "Unstop is a JS-rendered SPA (college hiring platform)",
    ),
    (
        "shine",
        "https://www.shine.com/login/",
        "Shine requires login and session controls",
    ),
    (
        "freshersworld",
        "https://www.freshersworld.com/",
        "Freshersworld serves a JS shell with no public API",
    ),
]


def run_instahyre(search_queries, locations=None):
    return probe_result(*PROVIDERS[0])


def run_cutshort(search_queries, locations=None):
    return probe_result(*PROVIDERS[1])


def run_unstop(search_queries, locations=None):
    return probe_result(*PROVIDERS[2])


def run_shine(search_queries, locations=None):
    return probe_result(*PROVIDERS[3])


def run_freshersworld(search_queries, locations=None):
    return probe_result(*PROVIDERS[4])