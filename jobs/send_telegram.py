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
        f"🎯 Job Agent: {len(jobs)} new matching job(s) found",
        "",
        "Sources: FreeHire + JobSpy",
    ]

    for index, job in enumerate(jobs, start=1):
        source = job.get("source", "FreeHire")

        lines.extend(
            [
                "",
                f"{index}. {job.get('match_score', 0)}% — "
                f"{job.get('match_category', 'Match')}",
                job.get("title", "Unknown role"),
                (
                    f"{job.get('company', job.get('company_name', 'Unknown company'))}"
                    f" | {job.get('location', 'Unknown location')}"
                ),
                f"Source: {source}",
                f"Apply: {job.get('url') or job.get('job_url', '')}",
            ]
        )

    return "\n".join(lines)


def no_new_jobs_message():
    return (
        "Heyyy Siva 👋\n\n"
        "No new job roles were found as of now, "
        "I'll try again in the next 3 hours."
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

    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

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
