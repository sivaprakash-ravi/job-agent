"""Small local checks for the job matching rules.

Run with: python jobs/test_job_matcher.py
"""

from job_matcher import keep_relevant_jobs, rank_jobs, score_job


strong_match = {
    "title": "Cloud Support Engineer",
    "location": "Bangalore, India",
    "skills": ["GCP", "Linux", "Python", "SQL", "Docker", "Kubernetes"],
    "experience_requirement": "1-2 years",
}

poor_match = {
    "title": "SAP ABAP Developer",
    "location": "Noida, India",
    "skills": ["SAP", "ABAP"],
    "experience_requirement": "4+ years",
}

close_role_match = {
    "title": "Application Support Analyst",
    "location": "Pune, India",
    "skills": ["SQL", "Postman", "Application Monitoring"],
}

strong_result = score_job(strong_match)
poor_result = score_job(poor_match)

assert strong_result["match_category"] in {"Excellent match", "Good match"}
assert poor_result["match_category"] == "Ignore"
assert strong_result["match_score"] > poor_result["match_score"]
assert score_job(close_role_match)["match_score"] >= 45

ranked = rank_jobs([poor_match, strong_match])
assert ranked[0]["title"] == "Cloud Support Engineer"
assert len(keep_relevant_jobs(ranked)) == 1

print("Job matcher checks passed.")
