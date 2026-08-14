"""Small local checks for the job matching rules.

Run with: python jobs/test_job_matcher.py
"""

from job_matcher import keep_relevant_jobs, rank_jobs, score_job


strong_match = {
    "title": "Cloud Support Engineer",
    "location": "Bangalore, India",
    "skills": ["GCP", "Linux", "Python", "SQL", "Docker", "Kubernetes"],
    "work_mode": "hybrid",
    "enrichment": {"employment_type": "full_time", "experience_years_min": 2},
}

poor_match = {
    "title": "SAP ABAP Developer",
    "location": "Noida, India",
    "skills": ["SAP", "ABAP"],
    "work_mode": "hybrid",
    "enrichment": {"employment_type": "full_time", "experience_years_min": 4},
}

close_role_match = {
    "title": "Application Support Analyst",
    "location": "Pune, India",
    "skills": ["SQL", "Postman", "Application Monitoring"],
    "work_mode": "remote",
    "enrichment": {"employment_type": "full_time", "experience_years_min": 2},
}

strong_result = score_job(strong_match)
poor_result = score_job(poor_match)

assert strong_result["match_category"] in {"Excellent match", "Good match"}
assert poor_result["match_category"] == "Ignore"
assert strong_result["match_score"] > poor_result["match_score"]
assert score_job(close_role_match)["match_score"] >= 45
assert poor_result["match_details"]["filter_reasons"] == [
    "Outside preferred locations",
    "Requires more than 2 years of experience",
    "Not enough target-role or skill overlap",
]

ranked = rank_jobs([poor_match, strong_match])
assert ranked[0]["title"] == "Cloud Support Engineer"
assert len(keep_relevant_jobs(ranked)) == 1

print("Job matcher checks passed.")
