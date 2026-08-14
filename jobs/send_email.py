"""Email the current shortlist after a successful job-agent run."""

import json
import os
import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path


REPORT_FILE = Path("reports/jobs.json")


def job_line(job):
    title = job.get("title", "Unknown role")
    company = job.get("company", "Unknown company")
    location = job.get("location", "Unknown location")
    score = job.get("match_score", 0)
    category = job.get("match_category", "Match")
    url = job.get("url", "")
    return f"{score}% — {category}\n{title}\n{company} | {location}\nApply: {url}"


def main():
    jobs = json.loads(REPORT_FILE.read_text(encoding="utf-8"))
    if not jobs:
        print("No matching jobs today. Email not sent.")
        return

    sender = os.environ["GMAIL_USERNAME"]
    password = os.environ["GMAIL_APP_PASSWORD"]
    recipient = os.environ["JOB_ALERT_EMAIL"]

    message = EmailMessage()
    message["Subject"] = f"Job Agent: {len(jobs)} matching job(s) found"
    message["From"] = sender
    message["To"] = recipient
    message.set_content(
        "Your Daily Job Agent found these matching jobs:\n\n"
        + "\n\n".join(job_line(job) for job in jobs)
    )

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
        server.login(sender, password)
        server.send_message(message)

    print(f"Email alert sent for {len(jobs)} matching job(s).")


if __name__ == "__main__":
    main()
