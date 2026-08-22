"""Send the current job shortlist to the user's Telegram chat."""

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


REPORT_FILE = Path("reports/jobs.json")

# Telegram sendMessage allows up to 4096 characters.
# Keep a little safety margin.
MAX_MESSAGE_LENGTH = 3900


def telegram_request(token, method, data=None):
    """Call the Telegram Bot API."""

    url = (
        f"https://api.telegram.org/"
        f"bot{token}/{method}"
    )

    request_data = None

    if data is not None:
        request_data = urllib.parse.urlencode(
            data
        ).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=request_data,
        method="POST",
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=30,
        ) as response:

            result = json.loads(
                response.read().decode(
                    "utf-8"
                )
            )

    except urllib.error.HTTPError as error:

        error_body = ""

        try:
            error_body = (
                error.read()
                .decode("utf-8")
            )
        except Exception:
            pass

        raise RuntimeError(
            "Telegram API HTTP error "
            f"{error.code}: "
            f"{error_body}"
        ) from error

    except urllib.error.URLError as error:

        raise RuntimeError(
            "Could not connect to "
            f"Telegram API: {error}"
        ) from error

    if not result.get("ok"):

        raise RuntimeError(
            "Telegram API error: "
            f"{result}"
        )

    return result["result"]


def get_chat_id():
    """
    Get TELEGRAM_CHAT_ID from GitHub Actions secrets.

    We no longer depend on getUpdates to discover
    the chat every time.
    """

    chat_id = os.environ.get(
        "TELEGRAM_CHAT_ID"
    )

    if not chat_id:
        raise RuntimeError(
            "TELEGRAM_CHAT_ID is not configured."
        )

    return chat_id.strip()


def format_message(jobs):
    """Build the main Telegram job report."""

    lines = [
        "Hi Siva 👋",
        "",
        "I’ve picked the jobs that could fit "
        "your profile from the recent search.",
        "",
        (
            f"🎯 {len(jobs)} new matching "
            "job(s) found"
        ),
        "",
        "Sources: JobSpy + FreeHire",
    ]

    for index, job in enumerate(
        jobs,
        start=1,
    ):

        source = (
            job.get("source")
            or "Unknown"
        )

        title = (
            job.get("title")
            or "Unknown role"
        )

        company = (
            job.get("company")
            or job.get(
                "company_name"
            )
            or "Unknown company"
        )

        location = (
            job.get("location")
            or "Unknown location"
        )

        url = (
            job.get("url")
            or job.get("job_url")
            or ""
        )

        score = job.get(
            "match_score",
            0,
        )

        category = job.get(
            "match_category",
            "Match",
        )

        lines.extend(
            [
                "",
                (
                    f"{index}. {score}% — "
                    f"{category}"
                ),
                title,
                (
                    f"{company} | "
                    f"{location}"
                ),
                f"Source: {source}",
                f"Apply: {url}",
            ]
        )

    lines.extend(
        [
            "",
            "Regards,",
            "Nova — Siva’s Job Assistant 🤖",
        ]
    )

    return "\n".join(lines)


def no_new_jobs_message():
    """Message when there are no new jobs."""

    return (
        "Hi Siva 👋\n\n"
        "No new matching job roles were found "
        "in this search cycle.\n\n"
        "I’ll check again in the next 3 hours.\n\n"
        "Regards,\n"
        "Nova — Siva’s Job Assistant 🤖"
    )


def split_message(
    message,
    max_length=MAX_MESSAGE_LENGTH,
):
    """
    Split a large Telegram message into safe chunks.

    We split on job blocks/new lines instead of
    cutting a job URL in half.
    """

    if len(message) <= max_length:
        return [message]

    lines = message.split("\n")

    chunks = []
    current = ""

    for line in lines:

        candidate = (
            f"{current}\n{line}"
            if current
            else line
        )

        if len(candidate) <= max_length:

            current = candidate

        else:

            if current:
                chunks.append(
                    current
                )

            # Extremely long individual line.
            # Split it safely if necessary.
            if len(line) > max_length:

                start = 0

                while start < len(line):

                    end = (
                        start
                        + max_length
                    )

                    chunks.append(
                        line[
                            start:end
                        ]
                    )

                    start = end

                current = ""

            else:

                current = line

    if current:
        chunks.append(current)

    return chunks


def send_job_report(
    token,
    chat_id,
    message,
):
    """Send one or more Telegram messages."""

    chunks = split_message(
        message
    )

    print(
        f"Telegram message length: "
        f"{len(message)} characters"
    )

    print(
        f"Telegram message chunks: "
        f"{len(chunks)}"
    )

    for index, chunk in enumerate(
        chunks,
        start=1,
    ):

        telegram_request(
            token,
            "sendMessage",
            {
                "chat_id": chat_id,
                "text": chunk,
                "disable_web_page_preview": "true",
            },
        )

        print(
            f"Telegram chunk "
            f"{index}/{len(chunks)} sent."
        )


def main():

    # ---------------------------------------------------------
    # Check report.
    # ---------------------------------------------------------

    if not REPORT_FILE.exists():

        print(
            "No job report found. "
            "Telegram alert not sent."
        )

        return

    try:

        jobs = json.loads(
            REPORT_FILE.read_text(
                encoding="utf-8"
            )
        )

    except json.JSONDecodeError as error:

        raise RuntimeError(
            "reports/jobs.json contains "
            f"invalid JSON: {error}"
        ) from error

    if not isinstance(
        jobs,
        list,
    ):
        raise RuntimeError(
            "reports/jobs.json must contain "
            "a JSON list."
        )

    # ---------------------------------------------------------
    # Telegram credentials.
    # ---------------------------------------------------------

    token = os.environ.get(
        "TELEGRAM_BOT_TOKEN"
    )

    if not token:

        print(
            "Telegram token not configured."
        )

        return

    chat_id = get_chat_id()

    # ---------------------------------------------------------
    # Build message.
    # ---------------------------------------------------------

    if not jobs:

        message = (
            no_new_jobs_message()
        )

    else:

        message = format_message(
            jobs
        )

    # ---------------------------------------------------------
    # Send.
    # ---------------------------------------------------------

    send_job_report(
        token=token,
        chat_id=chat_id,
        message=message,
    )

    print(
        "Telegram alert sent successfully."
    )


if __name__ == "__main__":
    main()