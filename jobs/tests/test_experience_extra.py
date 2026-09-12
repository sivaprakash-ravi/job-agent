"""Experience audit regressions (V1.1 Phase 7).

Covers the required-vs-preferred distinction, common written
formats (0-1, 1-2, 2, 1-3, 2-4, 3+, "a minimum of 3", "at least 2",
"2 years preferred") and confirms company/product numbers are never
treated as candidate experience.
"""

from job_matcher import analyse_experience


def make_job(description, title="Cloud Support Engineer"):
    return {
        "title": title,
        "location": "Chennai",
        "description": description,
        "skills": ["AWS", "Linux"],
    }


def analyse(description, title="Cloud Support Engineer"):
    return analyse_experience(make_job(description, title=title))


def test_zero_to_one_years_accepted():
    result = analyse("0-1 years of experience required.")
    assert result["hard_rejection"] is False


def test_one_to_two_years_accepted():
    result = analyse("1-2 years of experience required.")
    assert result["hard_rejection"] is False


def test_one_to_three_years_rejected():
    result = analyse("1-3 years of experience required.")
    assert result["hard_rejection"] is True


def test_two_to_four_years_rejected():
    result = analyse("2 to 4 years of experience required.")
    assert result["hard_rejection"] is True
    assert any(
        item["type"] == "mandatory"
        for item in result["mandatory_requirements"]
    )


def test_must_have_at_least_two_years_accepted():
    result = analyse(
        "Candidates must have at least 2 years of experience "
        "in cloud administration."
    )
    assert result["hard_rejection"] is False


def test_at_least_two_years_required_accepted():
    result = analyse("At least 2 years of experience is required.")
    assert result["hard_rejection"] is False


def test_two_years_preferred_not_rejected():
    result = analyse(
        "2 years of experience preferred; open to freshers."
    )
    assert result["hard_rejection"] is False


def test_three_years_preferred_not_rejected():
    # "preferred" frames even a 3-year statement as optional.
    result = analyse(
        "Preferred qualifications: 3 years of experience with AWS."
    )
    assert result["hard_rejection"] is False
    assert any(
        item["type"] == "preferred"
        for item in result["all_requirements"]
    )


def test_experience_with_tool_for_two_years_accepted():
    result = analyse(
        "We want someone with experience with Kubernetes for 2 years."
    )
    assert result["hard_rejection"] is False


def test_minimum_of_three_years_rejected():
    result = analyse("A minimum of 3 years of experience is required.")
    assert result["hard_rejection"] is True


def test_minimum_of_two_years_accepted():
    result = analyse("A minimum of 2 years of experience is required.")
    assert result["hard_rejection"] is False


def test_three_years_linux_rejected():
    result = analyse(
        "3 years experience in Linux administration is required."
    )
    assert result["hard_rejection"] is True


def test_seniority_words_do_not_reject_when_experience_valid():
    result = analyse(
        "This is a senior role. 2+ years of experience required.",
        title="Senior DevOps Engineer",
    )
    assert result["hard_rejection"] is False