"""Send the daily company and role summary to Telegram."""

import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path


HISTORY_FILE = Path("reports/daily_job_history.json")

IST = timezone(
    timedelta(hours=5, minutes=30)
)


def telegram_request(token, method, data=None):
    url = f"https://api.telegram.org/bot{token}/{method}"

    request_data = None

    if data is not None:
        request_data = urllib.parse.urlencode(data).encode(
            "utf-8"
        )

    request = urllib.request.Request(
        url,
        data=request_data,
    )

    with urllib.request.urlopen(
        request,
        timeout=30,
    ) as response:
        result = json.loads(
            response.read().decode("utf-8")
        )

    if not result.get("ok"):
        raise RuntimeError(
            f"Telegram API error: {result}"
        )

    return result["result"]


def today_ist():
    return datetime.now(IST).date().isoformat()


def build_summary(jobs):
    companies = {}

    for job in jobs:
        company = (
            job.get("company")
            or job.get("company_name")
            or "Unknown company"
        )

        title = (
            job.get("title")
            or "Unknown role"
        )

        company = str(company).strip()
        title = str(title).strip()

        if company not in companies:
            companies[company] = set()

        companies[company].add(title)

    lines = [
        "Hi Siva 👋",
        "",
        "Here’s your job-search summary for today.",
        "I’ve picked out the companies and roles "
        "that matched your profile:",
        "",
        "🏢 Companies & Roles",
    ]

    for index, company in enumerate(
        sorted(companies),
        start=1,
    ):
        lines.append("")
        lines.append(f"{index}. {company}")

        for title in sorted(
            companies[company]
        ):
            lines.append(
                f"   • {title}"
            )

    total_companies = len(companies)

    total_roles = sum(
        len(roles)
        for roles in companies.values()
    )

    lines.extend(
        [
            "",
            "📊 Today",
            f"Companies: {total_companies}",
            f"Unique roles: {total_roles}",
            f"New matching jobs: {len(jobs)}",
            "",
            "Regards,",
            "Nova 🤖",
            "Siva’s Job Assistant",
        ]
    )

    return "\n".join(lines)


def main():
    token = os.environ.get(
        "TELEGRAM_BOT_TOKEN"
    )

    chat_id = os.environ.get(
        "TELEGRAM_CHAT_ID"
    )

    if not token:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN is not configured."
        )

    if not chat_id:
        raise RuntimeError(
            "TELEGRAM_CHAT_ID is not configured."
        )

    if not HISTORY_FILE.exists():
        print(
            "No daily job history found. "
            "Summary not sent."
        )
        return

    history = json.loads(
        HISTORY_FILE.read_text(
            encoding="utf-8"
        )
    )

    date_key = today_ist()
    jobs = history.get(
        date_key,
        [],
    )

    if not jobs:
        message = (
            "Hi Siva 👋\n\n"
            "There were no new matching jobs "
            "recorded today.\n\n"
            "Regards,\n"
            "Nova 🤖\n"
            "Siva’s Job Assistant"
        )
    else:
        message = build_summary(jobs)

    telegram_request(
        token,
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": message,
            "disable_web_page_preview": "true",
        },
    )

    print(
        f"Daily summary sent for {date_key}."
    )


if __name__ == "__main__":
    main()
