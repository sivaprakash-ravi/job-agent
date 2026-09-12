"""V1.1.1 score-gate regression tests.

Explicit qualification states:

    qualified      = no hard filter reason AND score >= MINIMUM_SCORE
    possible_match = no hard filter reason BUT score < MINIMUM_SCORE
    rejected       = hard filter reason (hard rejection always wins)

Telegram sends ONLY new + qualified jobs.
"""

import collect_jobs
from job_matcher import (
    MINIMUM_SCORE,
    POSSIBLE_MATCH,
    QUALIFIED,
    REJECTED,
    get_rejected_jobs,
    job_qualification,
    keep_possible_matches,
    keep_relevant_jobs,
)


def ranked(score, filter_reasons=None, qualification=None, key="job-1"):
    return {
        "source": "workable",
        "source_job_id": key,
        "title": f"DevOps Engineer {key}",
        "company": f"Acme {key}",
        "location": "Chennai",
        "url": f"https://jobs.workable.com/view/{key}/devops-engineer",
        "match_score": score,
        "qualification": (
            qualification
            if qualification is not None
            else job_qualification(
                {
                    "match_score": score,
                    "match_details": {
                        "filter_reasons": filter_reasons or [],
                    },
                }
            )
        ),
        "match_details": {
            "filter_reasons": filter_reasons or [],
        },
    }


def test_MIMIMUM_SCORE_is_configured_45():
    assert MINIMUM_SCORE == 45


def test_score_44_is_possible_match():
    assert job_qualification(
        {"match_score": 44, "match_details": {"filter_reasons": []}}
    ) == POSSIBLE_MATCH


def test_score_45_is_qualified():
    assert job_qualification(
        {"match_score": 45, "match_details": {"filter_reasons": []}}
    ) == QUALIFIED


def test_score_46_is_qualified():
    assert job_qualification(
        {"match_score": 46, "match_details": {"filter_reasons": []}}
    ) == QUALIFIED


def test_hard_rejection_beats_score_100():
    result = job_qualification(
        {
            "match_score": 100,
            "match_details": {
                "filter_reasons": ["Not full-time"],
            },
        }
    )

    assert result == REJECTED


def test_keep_relevant_only_qualifies_score_gate():
    jobs = [
        ranked(44, key="a"),
        ranked(45, key="b"),
        ranked(46, key="c"),
    ]

    relevant = keep_relevant_jobs(jobs)

    assert [job["match_score"] for job in relevant] == [45, 46]


def test_keep_possible_returns_below_gate():
    jobs = [
        ranked(44, key="a"),
        ranked(45, key="b"),
    ]

    possible = keep_possible_matches(jobs)

    assert [job["match_score"] for job in possible] == [44]


def test_get_rejected_excludes_low_score_no_reason_jobs():
    jobs = [
        ranked(44, key="a"),
        ranked(100, filter_reasons=["Outside preferred locations"], key="b"),
    ]

    rejected = get_rejected_jobs(jobs)

    assert [job["match_score"] for job in rejected] == [100]


def test_telegram_sends_only_new_qualified():
    sent = set()

    new_jobs = collect_jobs.new_qualified_jobs(
        [
            ranked(46, key="new-qualified"),
            ranked(44, key="possible-low"),
            ranked(100, filter_reasons=["Not full-time"], key="hard-rejected"),
        ],
        sent,
    )

    assert [job["source_job_id"] for job in new_jobs] == ["new-qualified"]


def test_telegram_skips_possible_match():
    sent = set()

    candidates = collect_jobs.new_qualified_jobs(
        [ranked(44, key="possible-low")],
        sent,
    )

    assert candidates == []
    assert not sent


def test_telegram_skips_hard_rejected_even_at_100():
    sent = set()

    candidates = collect_jobs.new_qualified_jobs(
        [ranked(100, filter_reasons=["Not full-time"], key="hr")],
        sent,
    )

    assert candidates == []
    assert not sent


def test_telegram_skips_already_sent_qualified():
    job = ranked(46, key="already-sent")

    sent = {
        "url:https://jobs.workable.com/view/already-sent/devops-engineer"
    }

    candidates = collect_jobs.new_qualified_jobs([job], sent)

    assert candidates == []


def test_telegram_marks_new_qualified_as_sent():
    job = ranked(46, key="brand-new")

    sent = set()

    collect_jobs.new_qualified_jobs([job], sent)

    assert "url:https://jobs.workable.com/view/brand-new/devops-engineer" in sent