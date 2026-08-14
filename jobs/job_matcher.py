"""Simple, rule-based job matching for the daily job agent."""

import re

from profile import (
    EMPLOYMENT_TYPE,
    EXPERIENCE_YEARS,
    LOCATIONS,
    MAX_JOB_EXPERIENCE_YEARS,
    SKILLS,
    TARGET_ROLES,
)


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


def job_value(job, field_name):
    """Read a field from the job, including FreeHire's enrichment data."""
    return job.get(field_name) or job.get("enrichment", {}).get(field_name)


def matches_target_role(title, job_text, role):
    """Allow close title variations and clear DevOps/SRE mentions."""
    family = role_family(role)
    if contains_phrase(title, role) or contains_phrase(title, family):
        return True
    return family in {"devops", "sre"} and contains_phrase(job_text, family)


def required_experience(job):
    """Find required years, including FreeHire's enrichment value."""
    value = job_value(job, "experience_years_min")
    if value is None:
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

    matched_roles = [role for role in TARGET_ROLES if matches_target_role(title, job_text, role)]
    matched_skills = [skill for skill in SKILLS if contains_phrase(job_text, skill)]
    work_mode = normalise(job.get("work_mode"))
    matched_locations = [place for place in LOCATIONS if contains_phrase(location, place)]
    if contains_phrase(work_mode, "remote"):
        matched_locations.append("Remote")

    role_score = min(35, len(matched_roles) * 35)
    skill_score = min(40, len(matched_skills) * 4)
    location_score = 15 if matched_locations else 0

    required_years = required_experience(job)
    experience_score = 0
    experience_note = "No experience requirement found"
    if required_years is None:
        experience_score = 5
    elif required_years <= MAX_JOB_EXPERIENCE_YEARS:
        experience_score = 10
        experience_note = f"Requires about {required_years:g} years: suitable"
    else:
        experience_score = -20
        experience_note = (
            f"Requires about {required_years:g} years: above your "
            f"{MAX_JOB_EXPERIENCE_YEARS:g}-year limit"
        )

    score = max(0, min(100, role_score + skill_score + location_score + experience_score))
    employment_type = normalise(job_value(job, "employment_type"))
    filter_reasons = []
    if employment_type != EMPLOYMENT_TYPE:
        filter_reasons.append("Not a full-time role")
    if not matched_locations:
        filter_reasons.append("Outside preferred locations")
    if required_years is not None and required_years > MAX_JOB_EXPERIENCE_YEARS:
        filter_reasons.append("Requires more than 2 years of experience")
    if not matched_roles and len(matched_skills) < 6:
        filter_reasons.append("Not enough target-role or skill overlap")

    passes_filters = not filter_reasons
    ranked_job = dict(job)
    ranked_job["match_score"] = score
    ranked_job["match_category"] = category_for(score) if passes_filters else "Ignore"
    ranked_job["match_details"] = {
        "matched_roles": matched_roles,
        "matched_skills": matched_skills,
        "matched_locations": matched_locations,
        "experience_note": experience_note,
        "employment_type": employment_type or "Not listed",
        "work_mode": work_mode or "Not listed",
        "filter_reasons": filter_reasons,
    }
    return ranked_job


def rank_jobs(jobs):
    """Score every job and return the best matches first."""
    ranked_jobs = [score_job(job) for job in jobs]
    return sorted(ranked_jobs, key=lambda job: job["match_score"], reverse=True)


def keep_relevant_jobs(ranked_jobs):
    """Keep only jobs that meet every user requirement."""
    return [
        job
        for job in ranked_jobs
        if job["match_score"] >= MINIMUM_SCORE
        and job["match_category"] != "Ignore"
    ]
