"""Experience extraction and classification tests."""

from job_matcher import analyse_experience


def make_job(description, title="Cloud Support Engineer", location="Chennai"):
    return {
        "title": title,
        "location": location,
        "description": description,
        "skills": ["GCP", "Linux", "SQL"],
    }


def analyse(description, title="Cloud Support Engineer"):
    return analyse_experience(
        make_job(description, title=title)
    )


def test_two_years_accepted():
    result = analyse("We require 2 years of experience.")
    assert result["hard_rejection"] is False
    assert result["valid"] is True


def test_plus_two_years_accepted():
    result = analyse("We need 2+ years of experience.")
    assert result["hard_rejection"] is False


def test_around_two_years_accepted():
    result = analyse("Around 2 years of experience required.")
    assert result["hard_rejection"] is False


def test_range_one_to_two_accepted():
    result = analyse("1-2 years of experience.")
    assert result["hard_rejection"] is False


def test_range_two_to_five_rejected():
    result = analyse("2-5 years of experience required.")
    assert result["hard_rejection"] is True


def test_plus_three_years_rejected():
    result = analyse("We need 3+ years of experience.")
    assert result["hard_rejection"] is True


def test_three_years_rejected():
    result = analyse("Minimum 3 years of experience.")
    assert result["hard_rejection"] is True


def test_at_least_three_years_rejected():
    result = analyse("At least 3 years of experience.")
    assert result["hard_rejection"] is True


def test_three_plus_years_not_preferred_due_to_plus_word():
    result = analyse(
        "You must have 3+ years of experience in cloud operations."
    )

    assert result["hard_rejection"] is True
    assert all(
        item["type"] == "mandatory"
        for item in result["mandatory_requirements"]
    )


def test_preferred_qualification_not_hard_rejected():
    result = analyse(
        "Preferred qualifications: 5+ years of experience "
        "with AWS and Linux administration. Apply today!" 
    )

    assert result["hard_rejection"] is False
    assert any(
        item["type"] == "preferred"
        for item in result["all_requirements"]
    )


def test_preferred_elsewhere_in_large_text_stays_mandatory():
    description = (
        "About us: We are a friendly remote-first team. "
        "A positive attitude is strongly preferred, and we value "
        "communication skills, time management, and a passion for "
        "learning. Collaboration is preferred but not required. "
        "We also like people who contribute to open source. "
        "Minimum 3 years of experience in Linux administration "
        "is required for this role."
    )

    result = analyse(description)

    assert result["hard_rejection"] is True


def test_plus_two_years_not_marked_preferred_by_plus_word():
    result = analyse(
        "Ideally you have a GitHub account, plus 2+ years of "
        "experience working on production systems."
    )

    assert result["hard_rejection"] is False

    mandatory = result["mandatory_requirements"]

    assert any(
        "+ years" in item["text"] and item["type"] == "mandatory"
        for item in mandatory
    )


def test_experience_inside_nested_enrichment_picked_up():
    job = make_job("")
    job["enrichment"] = {
        "experience_requirement": "2-5 years of experience",
    }

    result = analyse_experience(job)

    assert result["hard_rejection"] is True


def test_unrelated_numbers_not_treated_as_experience():
    job = make_job("")
    job["description"] = (
        "The company was founded 5 years ago and serves "
        "1 million users."
    )

    result = analyse_experience(job)

    assert result["hard_rejection"] is False


def test_employee_count_plus_not_treated_as_experience():
    job = make_job("")
    job["description"] = (
        "We are a fast-growing startup with 1,000+ employees "
        "across 4+ offices worldwide."
    )

    result = analyse_experience(job)

    assert result["hard_rejection"] is False

    numbers = [
        item["text"]
        for item in result["all_requirements"]
    ]

    assert not any(
        "000+" in text or text.endswith("+")
        for text in numbers
    )