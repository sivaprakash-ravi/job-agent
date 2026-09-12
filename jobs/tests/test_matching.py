"""Matching, ranking and filtering tests."""

from job_matcher import (
    keep_relevant_jobs,
    matches_location,
    rank_jobs,
    score_job,
)


def base_job():
    return {
        "title": "Cloud Support Engineer",
        "location": "Chennai, India",
        "description": (
            "Support GCP and Linux systems. 2 years of "
            "experience preferred. Full-time."
        ),
        "skills": ["GCP", "Linux", "SQL", "Python", "Docker"],
    }


def test_strong_match_passes():
    result = score_job(base_job())

    assert result["match_category"] != "Ignore"


def test_poor_match_rejected_with_reasons():
    job = {
        "title": "SAP ABAP Developer",
        "location": "Noida, India",
        "description": "5 years SAP experience. Full-time.",
        "skills": ["SAP", "ABAP"],
    }

    result = score_job(job)

    assert result["match_category"] == "Ignore"
    assert result["match_details"]["filter_reasons"]


def test_ranking_orders_best_first():
    good = base_job()
    bad = {
        "title": "SAP ABAP Developer",
        "location": "Noida, India",
        "description": "5 years SAP experience. Full-time.",
        "skills": ["SAP", "ABAP"],
    }

    ranked = rank_jobs([bad, good])

    assert ranked[0]["title"] == good["title"]
    assert ranked[0]["match_score"] >= ranked[1]["match_score"]


def test_keep_relevant_filters_ignored():
    good = base_job()

    bad = dict(good)
    bad["title"] = "SAP ABAP Developer"
    bad["location"] = "Noida, India"
    bad["description"] = "5 years SAP experience. Full-time."
    bad["skills"] = ["SAP", "ABAP"]

    ranked = rank_jobs([good, bad])

    relevant = keep_relevant_jobs(ranked)

    assert all(
        job["match_category"] != "Ignore"
        for job in relevant
    )
    assert len(relevant) == 1


def test_senior_title_not_hard_rejected():
    job = {
        "title": "Senior DevOps Engineer",
        "location": "Chennai, India",
        "description": "2+ years of experience. Full-time.",
        "skills": ["GCP", "Linux", "Docker", "Kubernetes", "CI/CD"],
    }

    result = score_job(job)

    assert result["match_category"] != "Ignore"


def test_experience_hard_gate_rejects():
    job = base_job()
    job["description"] = "Minimum 5 years of experience. Full-time."

    result = score_job(job)

    assert result["match_category"] == "Ignore"


def test_remote_location_matches():
    for location in [
        "Remote",
        "Remote, India",
        "Work from home",
        "Anywhere",
    ]:
        job = base_job()
        job["location"] = location

        assert matches_location(job), location


def test_all_profile_locations_match():
    for location in [
        "Chennai",
        "Chennai, Tamil Nadu, India",
        "Bangalore",
        "Bengaluru, Karnataka",
        "Hyderabad, Telangana",
        "Coimbatore",
        "Coimbatore, India",
    ]:
        assert matches_location(base_job_with(location)), location


def test_outside_locations_rejected():
    job = base_job_with("New Delhi, India")

    assert matches_location(job) is False

    result = score_job(job)

    assert result["match_category"] == "Ignore"


def test_part_time_rejected_when_full_time_expected():
    job = base_job()
    job["employment_type"] = "part-time"

    result = score_job(job)

    assert result["match_category"] == "Ignore"


def test_remote_flag_job_matches():
    job = base_job()
    job["location"] = "Remote"
    job["remote"] = True

    assert matches_location(job)


def base_job_with(location):
    job = base_job()
    job["location"] = location
    return job