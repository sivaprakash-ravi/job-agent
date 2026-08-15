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

    request = urllib.request.Request(url, data=request_data)

    with urllib.request.urlopen(request, timeout=30) as response:
        result = json.loads(response.read().decode("utf-8"))

    if not result.get("ok"):
        raise RuntimeError(f"Telegram API error: {result}")

    return result["result"]


def latest_private_chat_id(updates):
    """Use the chat where the owner most recently pressed Start."""
    for update in reversed(updates):
        message = update.get("message", {})
        chat = message.get("chat", {})

        if chat.get("type") == "private":
            return chat["id"]

    raise RuntimeError(
        "Open the bot in Telegram and press Start, then run again."
    )


def format_message(jobs):
    lines = [f"🎯 Job Agent: {len(jobs)} new job(s) found"]

    for job in jobs:
        lines.extend(
            [
                "",
                f"{job.get('match_score', 0)}% — "
                f"{job.get('match_category', 'Match')}",
                job.get("title", "Unknown role"),
                f"{job.get('company', 'Unknown company')} | "
                f"{job.get('location', 'Unknown location')}",
                f"Apply: {job.get('url', '')}",
            ]
        )

    return "\n".join(lines)


def no_new_jobs_message():
    return (
        "Hi Siva 👋\n\n"
        "No new job roles were found in this run.\n\n"
        "I'll try again in the next 3 hours. 🔎"
    )


def main():
    jobs = json.loads(REPORT_FILE.read_text(encoding="utf-8"))

    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = latest_private_chat_id(
        telegram_request(token, "getUpdates")
    )

    if not jobs:
        message = no_new_jobs_message()
        print("No new job roles found. Sending Telegram update.")
    else:
        message = format_message(jobs)
        print(f"Sending {len(jobs)} new job(s) to Telegram.")

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
