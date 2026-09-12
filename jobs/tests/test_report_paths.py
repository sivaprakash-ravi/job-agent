"""Deterministic report-path tests (V1.1.1).

All report/history paths resolve against the repository root, never
the current working directory. Running from the repo root or from
jobs/ must produce the exact same report directory and sent-history
file, so local runs can never silently use jobs/reports.
"""

import os
import subprocess
import sys

from pathlib import Path

import collect_jobs
import send_daily_summary
import send_email
import send_telegram
import update_daily_history

JOBS_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = JOBS_DIR.parent


def _resolve_via_subprocess(cwd):
    env = dict(os.environ)
    env["PYTHONPATH"] = str(JOBS_DIR)

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import collect_jobs"
                ";print(collect_jobs.OUTPUT_DIR)"
                ";print(collect_jobs.SENT_FILE)"
            ),
        ],
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )

    return result.stdout.strip().splitlines()


def test_output_dir_is_repo_root_reports():
    assert collect_jobs.OUTPUT_DIR == REPO_ROOT / "reports"


def test_sent_file_is_repo_root_reports_sent_jobs():
    assert collect_jobs.SENT_FILE == REPO_ROOT / "reports" / "sent_jobs.json"


def test_all_report_files_below_repo_root_reports():
    for path in (
        collect_jobs.OUTPUT_FILE,
        collect_jobs.FULL_OUTPUT_FILE,
        collect_jobs.REJECTED_OUTPUT_FILE,
        collect_jobs.UNVERIFIED_OUTPUT_FILE,
        collect_jobs.POSSIBLE_OUTPUT_FILE,
        collect_jobs.SENT_FILE,
        collect_jobs.SOURCE_STATS_FILE,
        collect_jobs.PROVIDER_HEALTH_FILE,
        collect_jobs.RUN_SUMMARY_FILE,
        collect_jobs.FUNNEL_FILE,
        collect_jobs.SKIPPED_FILE,
    ):
        assert path.resolve().is_relative_to(
            (REPO_ROOT / "reports").resolve()
        ), path


def test_same_paths_from_repo_root_and_jobs_dir():
    from_root = _resolve_via_subprocess(REPO_ROOT)
    from_jobs = _resolve_via_subprocess(JOBS_DIR)

    assert from_root == from_jobs
    assert from_root[0] == str(REPO_ROOT / "reports")
    assert from_root[1] == str(REPO_ROOT / "reports" / "sent_jobs.json")


def test_telegram_report_path_deterministic():
    assert send_telegram.REPORT_FILE == (
        REPO_ROOT / "reports" / "jobs.json"
    )


def test_email_report_path_deterministic():
    assert send_email.REPORT_FILE == (
        REPO_ROOT / "reports" / "jobs.json"
    )


def test_daily_summary_history_path_deterministic():
    assert send_daily_summary.HISTORY_FILE == (
        REPO_ROOT / "reports" / "daily_job_history.json"
    )


def test_update_daily_history_paths_deterministic():
    assert update_daily_history.JOBS_FILE == (
        REPO_ROOT / "reports" / "jobs.json"
    )

    assert update_daily_history.HISTORY_FILE == (
        REPO_ROOT / "reports" / "daily_job_history.json"
    )