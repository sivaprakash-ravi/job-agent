"""Simple, rule-based job matching for the daily job agent."""

import re

from profile import EXPERIENCE_YEARS, LOCATIONS, SKILLS, TARGET_ROLES


MINIMUM_SCORE = 45


def normalise(value):
    """Turn a value into lowercase text that is easy to search."""
    if isinstance(value, list):
        return " ".join(normalise(item) for item in value)
    if isinstance(value, dict):
        return " ".join(normalise(item) for item in value.values())
    return str(value or "").lower()


def contains_phrase(text, phrase):
    """Match whole words so, for example, 'SRE' is not part of another word."""
    pattern = r"(?<!\w)" + re.escape(phrase.lower()) + r"(?!\w)"
    return bool(re.search(pattern, text))


def get_job_text(job):
    """Combine the useful job fields into one searchable piece of text."""
    fields = [
        job.get("title"),
        job.get("description"),
        job.get("skills"),
        job.get("category"),
        job.get("seniority"),
    ]
    return normalise(fields)


def role_family(role):
    """Keep the meaningful part of a role title.

    This lets 'Application Support Analyst' match the target role
    'Application Support Engineer' without treating an unrelated analyst role
    as a match.
    """
    ignored_words = {"engineer", "junior", "senior"}
    words = [word for word in role.lower().split() if word not in ignored_words]
    return " ".join(words)


def required_experience(job):
    """Find the first number in an experience field, such as '4+ years'."""
    value = job.get("experience_requirement") or job.get("experience") or ""
    match = re.search(r"\d+(?:\.\d+)?", normalise(value))
    return float(match.group()) if match else None


def category_for(score):
    if score >= 80:
        return "Excellent match"
    if score >= 65:
        return "Good match"
    if score >= MINIMUM_SCORE:
        return "Possible match"
    return "Ignore"


def score_job(job):
    """Add matching details and a score to one FreeHire job dictionary.

    Score guide:
    - target role in the title: up to 35 points
    - relevant skills: up to 40 points
    - preferred location: 15 points
    - suitable experience requirement: 10 points
    - a role requiring much more experience: minus 20 points
    """
    title = normalise(job.get("title"))
    job_text = get_job_text(job)
    location = normalise(job.get("location"))

    matched_roles = [
        role
        for role in TARGET_ROLES
        if contains_phrase(title, role) or contains_phrase(title, role_family(role))
    ]
    matched_skills = [skill for skill in SKILLS if contains_phrase(job_text, skill)]
    matched_locations = [place for place in LOCATIONS if contains_phrase(location, place)]

    role_score = min(35, len(matched_roles) * 35)
    skill_score = min(40, len(matched_skills) * 4)
    location_score = 15 if matched_locations else 0

    required_years = required_experience(job)
    experience_score = 0
    experience_note = "No experience requirement found"
    if required_years is None:
        experience_score = 5
    elif required_years <= EXPERIENCE_YEARS + 1:
        experience_score = 10
        experience_note = f"Requires about {required_years:g} years: suitable"
    else:
        experience_score = -20
        experience_note = (
            f"Requires about {required_years:g} years: above your "
            f"{EXPERIENCE_YEARS:g} years"
        )

    score = max(0, min(100, role_score + skill_score + location_score + experience_score))
    ranked_job = dict(job)
    ranked_job["match_score"] = score
    ranked_job["match_category"] = category_for(score)
    ranked_job["match_details"] = {
        "matched_roles": matched_roles,
        "matched_skills": matched_skills,
        "matched_locations": matched_locations,
        "experience_note": experience_note,
    }
    return ranked_job


def rank_jobs(jobs):
    """Score every job and return the best matches first."""
    ranked_jobs = [score_job(job) for job in jobs]
    return sorted(ranked_jobs, key=lambda job: job["match_score"], reverse=True)


def keep_relevant_jobs(ranked_jobs):
    """Remove jobs marked Ignore from the short report."""
    return [job for job in ranked_jobs if job["match_score"] >= MINIMUM_SCORE]
