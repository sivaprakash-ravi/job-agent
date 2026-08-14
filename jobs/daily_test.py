from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
REPORT_DIR = BASE_DIR / "reports"

REPORT_DIR.mkdir(parents=True, exist_ok=True)

now = datetime.now()

report_file = REPORT_DIR / "daily_test.txt"

with open(report_file, "a", encoding="utf-8") as file:
    file.write(f"Automation ran successfully: {now:%Y-%m-%d %H:%M:%S}\n")

print(f"Automation completed: {now:%Y-%m-%d %H:%M:%S}")
print(f"Report: {report_file}")