"""Send the current job shortlist to the user's Telegram bot chat."""

import json
import os
import urllib.parse
import urllib.request
from pathlib import Path


REPORT_FILE = Path("reports/jobs.json")


def telegram_request(token, method, data=None):
    url = f"https://api.telegram.org/bot{token}/{method}"

    request_data = None

    if data is not None:
        request_data = urllib.parse.urlencode(data).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=request_data,
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        result = json.loads(
            response.read().decode("utf-8")
        )

    if not result.get("ok"):
        raise RuntimeError(
            f"Telegram API error: {result}"
        )

    return result["result"]


def format_message(jobs):
    lines = [
        "Hi Siva 👋",
        "",
        "I’ve picked out some jobs that could be a good "
        "fit for you from the recent searches:",
        "",
        "━━━━━━━━━━━━━━━━━━━━",
    ]

    for index, job in enumerate(jobs, start=1):
        source = job.get("source", "Unknown")
        title = job.get("title", "Unknown role")
        company = job.get(
            "company",
            job.get("company_name", "Unknown company"),
        )
        location = job.get(
            "location",
            "Unknown location",
        )
        score = job.get("match_score", 0)
        category = job.get(
            "match_category",
            "Match",
        )
        url = job.get("url") or job.get(
            "job_url",
            "",
        )

        lines.extend(
            [
                "",
                f"{index}. {title}",
                f"🏢 {company}",
                f"📍 {location}",
                f"🎯 {score}% — {category}",
                f"🔎 Source: {source}",
                f"🔗 Apply: {url}",
            ]
        )

    lines.extend(
        [
            "",
            "━━━━━━━━━━━━━━━━━━━━",
            "",
            "Regards,",
            "Nova 🤖",
            "Siva’s Job Assistant",
        ]
    )

    return "\n".join(lines)


def no_new_jobs_message():
    return (
        "Hi Siva 👋\n\n"
        "I couldn’t find any new matching roles in the recent search. "
        "I’ll check again in the next few hours.\n\n"
        "Regards,\n"
        "Nova 🤖\n"
        "Siva’s Job Assistant"
    )


def main():
    if not REPORT_FILE.exists():
        print("No job report found. Telegram alert not sent.")
        return

    jobs = json.loads(
        REPORT_FILE.read_text(
            encoding="utf-8"
        )
    )

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

    if not jobs:
        message = no_new_jobs_message()
    else:
        message = format_message(jobs)

    telegram_request(
        token,
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": message,
            "disable_web_page_preview": "true",
        },
    )

    print("Telegram alert sent successfully.")


if __name__ == "__main__":
    main()
