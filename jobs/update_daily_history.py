"""Store today's matching jobs for the daily summary."""

import json
from datetime import datetime, timezone
from pathlib import Path


JOBS_FILE = Path("reports/jobs.json")
HISTORY_FILE = Path("reports/daily_job_history.json")


def main():
    if not JOBS_FILE.exists():
        print("No jobs report found. Daily history not updated.")
        return

    jobs = json.loads(
        JOBS_FILE.read_text(encoding="utf-8")
    )

    today = datetime.now(
        timezone.utc
    ).date().isoformat()

    if HISTORY_FILE.exists():
        history = json.loads(
            HISTORY_FILE.read_text(
                encoding="utf-8"
            )
        )
    else:
        history = {}

    if not isinstance(history, dict):
        history = {}

    existing = history.get(today, [])

    if not isinstance(existing, list):
        existing = []

    seen = set()

    for job in existing:
        key = (
            str(
                job.get("company")
                or job.get("company_name")
                or ""
            ).lower().strip(),
            str(
                job.get("title")
                or ""
            ).lower().strip(),
        )
        seen.add(key)

    for job in jobs:
        key = (
            str(
                job.get("company")
                or job.get("company_name")
                or ""
            ).lower().strip(),
            str(
                job.get("title")
                or ""
            ).lower().strip(),
        )

        if key not in seen:
            existing.append(job)
            seen.add(key)

    history[today] = existing

    # Keep only the latest 7 days.
    recent_dates = sorted(history.keys())[-7:]
    history = {
        date: history[date]
        for date in recent_dates
    }

    HISTORY_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    HISTORY_FILE.write_text(
        json.dumps(
            history,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print(
        f"Saved {len(existing)} unique jobs "
        f"for {today}."
    )


if __name__ == "__main__":
    main()
