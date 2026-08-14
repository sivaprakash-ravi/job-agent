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
    raise RuntimeError("Open the bot in Telegram and press Start, then run again.")


def format_message(jobs):
    lines = [f"🎯 Job Agent: {len(jobs)} matching job(s) found"]
    for job in jobs:
        lines.extend(
            [
                "",
                f"{job.get('match_score', 0)}% — {job.get('match_category', 'Match')}",
                job.get("title", "Unknown role"),
                f"{job.get('company', 'Unknown company')} | {job.get('location', 'Unknown location')}",
                f"Apply: {job.get('url', '')}",
            ]
        )
    return "\n".join(lines)


def main():
    jobs = json.loads(REPORT_FILE.read_text(encoding="utf-8"))
    if not jobs:
        print("No matching jobs today. Telegram alert not sent.")
        return

    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = latest_private_chat_id(telegram_request(token, "getUpdates"))
    telegram_request(
        token,
        "sendMessage",
        {"chat_id": chat_id, "text": format_message(jobs), "disable_web_page_preview": "true"},
    )
    print(f"Telegram alert sent for {len(jobs)} matching job(s).")


if __name__ == "__main__":
    main()
