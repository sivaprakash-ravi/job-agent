"""Targeted relevance-gate regression tests.

The relevance gate must be driven by the role family in the TITLE:

- a strong target-family title stays relevant even with an empty
  fetched JD (no >=4 skill requirement)
- a title outside the target families must NOT pass just because
  the description contains enough generic skills
"""

from job_matcher import score_job


def family_title_only(title, location="Chennai, India"):
    return {
        "title": title,
        "location": location,
    }


def generic_skills_job(title):
    return {
        "title": title,
        "location": "Chennai, India",
        "description": (
            "5 years AWS, Python, Java, SQL and CI/CD experience."
        ),
        "skills": ["AWS", "Python", "Java", "SQL", "CI/CD"],
    }


def test_cloud_infrastructure_support_engineer_empty_jd_relevant():
    result = score_job(
        family_title_only(
            "Cloud Infrastructure Support Engineer"
        )
    )

    assert result["match_category"] != "Ignore"
    assert result["match_details"]["matched_roles"]


def test_infrastructure_support_engineer_empty_jd_relevant():
    result = score_job(
        family_title_only(
            "Infrastructure Support Engineer"
        )
    )

    assert result["match_category"] != "Ignore"
    assert result["match_details"]["matched_roles"]


def test_infrastructure_engineer_empty_jd_relevant():
    result = score_job(
        family_title_only(
            "Infrastructure Engineer"
        )
    )

    assert result["match_category"] != "Ignore"
    assert result["match_details"]["matched_roles"]


def test_google_cloud_infrastructure_support_empty_jd_relevant():
    result = score_job(
        family_title_only(
            "Google Cloud Infrastructure Support Engineer"
        )
    )

    assert result["match_category"] != "Ignore"
    assert result["match_details"]["matched_roles"]


def test_senior_core_infrastructure_engineer_empty_jd_relevant():
    result = score_job(
        family_title_only(
            "Senior Core Infrastructure Engineer"
        )
    )

    assert result["match_category"] != "Ignore"
    assert result["match_details"]["matched_roles"]


def test_strong_family_title_outside_profile_location_ignored():
    result = score_job(
        family_title_only(
            "Cloud Infrastructure Support Engineer",
            location="New Delhi, India",
        )
    )

    assert result["match_category"] == "Ignore"
    assert "Outside preferred locations" in (
        result["match_details"]["filter_reasons"]
    )


def test_unrelated_job_with_four_generic_skills_rejected():
    result = score_job(
        generic_skills_job("Account Executive")
    )

    assert result["match_category"] == "Ignore"
    assert "Insufficient role/skill relevance" in (
        result["match_details"]["filter_reasons"]
    )


def test_full_stack_developer_generic_skills_rejected():
    result = score_job(
        generic_skills_job("Full Stack Developer")
    )

    assert result["match_category"] == "Ignore"


def test_engineering_manager_generic_skills_rejected():
    result = score_job(
        generic_skills_job("Engineering Manager")
    )

    assert result["match_category"] == "Ignore"


def test_principal_data_engineer_generic_skills_rejected():
    result = score_job(
        generic_skills_job("Principal Data Engineer")
    )

    assert result["match_category"] == "Ignore"


def test_sde_full_stack_generic_skills_rejected():
    result = score_job(
        generic_skills_job(
            "Software Development Engineer II Full Stack"
        )
    )

    assert result["match_category"] == "Ignore"


def test_empty_jd_non_family_title_rejected():
    result = score_job(
        family_title_only(
            "Billing Specialist"
        )
    )

    assert result["match_category"] == "Ignore"


def test_generic_skills_do_not_report_roles():
    result = score_job(
        generic_skills_job("Account Executive")
    )

    assert result["match_details"]["matched_roles"] == []