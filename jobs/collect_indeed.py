"""Legacy JobSpy discovery script (backward compatible).

Delegates to the JobSpy source adapter and saves the normalized
result to reports/indeed_jobs.json.

The main pipeline (collect_jobs.py) already includes JobSpy through
the source-runner, so this script is only kept as a convenience.
"""

import json
import os
from pathlib import Path

from sources.base import build_locations, build_search_queries
from sources.jobspy_source import run


OUTPUT_DIR = Path("reports")
OUTPUT_FILE = OUTPUT_DIR / "indeed_jobs.json"


def main():

    OUTPUT_DIR.mkdir(
        exist_ok=True
    )

    query_cap = int(
        os.environ.get("JOB_AGENT_QUERIES") or 0
    ) or None

    queries = build_search_queries(
        limit=query_cap
    )

    locations = build_locations()

    result = run(
        queries,
        locations,
    )

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            result.get("jobs", []),
            file,
            indent=2,
            ensure_ascii=False,
        )

    print(
        f"JobSpy status  : {result.get('status')}"
    )

    print(
        f"JobSpy count   : {result.get('count')}"
    )

    if result.get("error"):
        print(
            f"JobSpy error   : {result['error']}"
        )

    print(
        f"Saved to       : {OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()