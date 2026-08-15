"""Rule-based job matching for the daily job agent."""

import re

from profile import (
    EMPLOYMENT_TYPE,
    LOCATIONS,
    MAX_JOB_EXPERIENCE_YEARS,
    SKILLS,
    TARGET_ROLES,
)


MINIMUM_SCORE = 45


LOCATION_ALIASES = {
    "Chennai": [
        "chennai",
        "tamil nadu",
        "tamilnadu",
        "tn",
    ],
    "Bangalore": [
        "bangalore",
        "bengaluru",
        "karnataka",
        "ka",
    ],
    "Hyderabad": [
        "hyderabad",
        "telangana",
        "ts",
    ],
    "Coimbatore": [
        "coimbatore",
        "tamil nadu",
        "tamilnadu",
        "tn",
    ],
    "Remote": [
        "remote",
        "work from home",
        "wfh",
        "anywhere",
    ],
}


def normalise(value):
    """Turn a value into lowercase searchable text."""

    if isinstance(value, list):
        return " ".join(
            normalise(item)
            for item in value
        )

    if isinstance(value, dict):
        return " ".join(
            normalise(item)
            for item in value.values()
        )

    return str(value or "").lower()


def contains_phrase(text, phrase):
    """Match whole words."""

    text = normalise(text)
    phrase = normalise(phrase).strip()

    if not text or not phrase:
        return False

    pattern = (
        r"(?<!\w)"
        + re.escape(phrase)
        + r"(?!\w)"
    )

    return bool(re.search(pattern, text))


def get_job_text(job):
    """Combine useful job fields into searchable text."""

    fields = [
        job.get("title"),
        job.get("description"),
        job.get("skills"),
        job.get("category"),
        job.get("seniority"),
        job.get("job_type"),
    ]

    return normalise(fields)


def role_family(role):
    """
    Keep the meaningful part of a role title.

    This allows close title variations such as:
    Application Support Analyst
    Application Support Engineer
    """

    ignored_words = {
        "engineer",
        "junior",
        "senior",
        "lead",
        "associate",
        "specialist",
        "analyst",
    }

    words = [
        word
        for word in role.lower().split()
        if word not in ignored_words
    ]

    return " ".join(words)


def job_value(job, field_name):
    """Read a field including optional enrichment data."""

    enrichment = job.get("enrichment", {})

    if not isinstance(enrichment, dict):
        enrichment = {}

    return (
        job.get(field_name)
        or enrichment.get(field_name)
    )


def matches_target_role(title, job_text, role):
    """Match target roles and sensible title variations."""

    family = role_family(role)

    if contains_phrase(title, role):
        return True

    if family and contains_phrase(title, family):
        return True

    # DevOps/SRE can legitimately appear in the description
    # when the title uses a close variation.
    if family in {"devops", "sre"}:
        return contains_phrase(
            job_text,
            family,
        )

    return False


def required_experience(job):
    """Find the minimum required experience."""

    value = job_value(
        job,
        "experience_years_min",
    )

    if value is None:
        value = (
            job.get("experience_requirement")
            or job.get("experience")
            or ""
        )

    match = re.search(
        r"\d+(?:\.\d+)?",
        normalise(value),
    )

    return (
        float(match.group())
        if match
        else None
    )


def alias_matches_location(location_text, alias):
    """
    Match a location alias.

    Short state abbreviations such as TN/KA/TS are only
    considered when they appear as standalone tokens.
    """

    alias = alias.lower().strip()

    if alias in {"tn", "ka", "ts"}:
        return bool(
            re.search(
                r"(?<![A-Za-z])"
                + re.escape(alias)
                + r"(?![A-Za-z])",
                location_text,
            )
        )

    return contains_phrase(
        location_text,
        alias,
    )


def matches_location(location, work_mode):
    """
    Match preferred locations using aliases rather than
    requiring exact job-board formatting.
    """

    location_text = normalise(location)
    work_mode_text = normalise(work_mode)

    matched = []

    for preferred_location in LOCATIONS:
        aliases = LOCATION_ALIASES.get(
            preferred_location,
            [preferred_location],
        )

        if any(
            alias_matches_location(
                location_text,
                alias,
            )
            for alias in aliases
        ):
            matched.append(preferred_location)

    if "Remote" in LOCATIONS:
        if any(
            alias_matches_location(
                work_mode_text,
                alias,
            )
            for alias in LOCATION_ALIASES["Remote"]
        ):
            matched.append("Remote")

        if any(
            alias_matches_location(
                location_text,
                alias,
            )
            for alias in LOCATION_ALIASES["Remote"]
        ):
            matched.append("Remote")

    return list(
        dict.fromkeys(matched)
    )


def category_for(score):
    if score >= 80:
        return "Excellent match"

    if score >= 65:
        return "Good match"

    if score >= MINIMUM_SCORE:
        return "Possible match"

    return "Ignore"


def score_job(job):
    """
    Score one job.

    Score guide:
    - target role: up to 35 points
    - relevant skills: up to 40 points
    - preferred location: 15 points
    - suitable/unknown experience: up to 10 points
    - excessive experience: minus 20 points
    """

    title = normalise(
        job.get("title")
    )

    job_text = get_job_text(job)

    location = normalise(
        job.get("location")
    )

    work_mode = normalise(
        job.get("work_mode")
        or job.get("remote_work_model")
        or (
            "remote"
            if job.get("is_remote")
            else ""
        )
    )

    matched_roles = [
        role
        for role in TARGET_ROLES
        if matches_target_role(
            title,
            job_text,
            role,
        )
    ]

    matched_skills = [
        skill
        for skill in SKILLS
        if contains_phrase(
            job_text,
            skill,
        )
    ]

    matched_locations = matches_location(
        location,
        work_mode,
    )

    role_score = min(
        35,
        len(matched_roles) * 35,
    )

    skill_score = min(
        40,
        len(matched_skills) * 4,
    )

    location_score = (
        15
        if matched_locations
        else 0
    )

    required_years = required_experience(job)

    experience_score = 0
    experience_note = (
        "No experience requirement found"
    )

    if required_years is None:
        # Unknown experience should not automatically
        # reject an otherwise relevant job.
        experience_score = 5

    elif required_years <= MAX_JOB_EXPERIENCE_YEARS:
        experience_score = 10
        experience_note = (
            f"Requires about {required_years:g} years: suitable"
        )

    else:
        experience_score = -20
        experience_note = (
            f"Requires about {required_years:g} years: "
            f"above your "
            f"{MAX_JOB_EXPERIENCE_YEARS:g}-year limit"
        )

    score = max(
        0,
        min(
            100,
            role_score
            + skill_score
            + location_score
            + experience_score,
        ),
    )

    employment_type = normalise(
        job_value(
            job,
            "employment_type",
        )
        or job.get("job_type")
    )

    filter_reasons = []

    # Only reject an explicitly incompatible employment type.
    # Missing employment type is allowed.
    if employment_type:
        if (
            EMPLOYMENT_TYPE == "full_time"
            and not any(
                term in employment_type
                for term in (
                    "full-time",
                    "full time",
                    "fulltime",
                )
            )
        ):
            filter_reasons.append(
                "Not a full-time role"
            )

    if not matched_locations:
        filter_reasons.append(
            "Outside preferred locations"
        )

    if (
        required_years is not None
        and required_years
        > MAX_JOB_EXPERIENCE_YEARS
    ):
        filter_reasons.append(
            "Requires more than "
            f"{MAX_JOB_EXPERIENCE_YEARS:g} "
            "years of experience"
        )

    # Require either a target-role match or meaningful
    # skill overlap.
    if (
        not matched_roles
        and len(matched_skills) < 4
    ):
        filter_reasons.append(
            "Not enough target-role or skill overlap"
        )

    passes_filters = not filter_reasons

    ranked_job = dict(job)

    ranked_job["match_score"] = score

    ranked_job["match_category"] = (
        category_for(score)
        if passes_filters
        else "Ignore"
    )

    ranked_job["match_details"] = {
        "matched_roles": matched_roles,
        "matched_skills": matched_skills,
        "matched_locations": matched_locations,
        "experience_note": experience_note,
        "employment_type": (
            employment_type
            or "Not listed"
        ),
        "work_mode": (
            work_mode
            or "Not listed"
        ),
        "filter_reasons": filter_reasons,
    }

    return ranked_job


def rank_jobs(jobs):
    """Score every job and return the best matches first."""

    ranked_jobs = [
        score_job(job)
        for job in jobs
    ]

    return sorted(
        ranked_jobs,
        key=lambda job: job["match_score"],
        reverse=True,
    )


def keep_relevant_jobs(ranked_jobs):
    """Keep jobs that meet the matching requirements."""

    return [
        job
        for job in ranked_jobs
        if (
            job["match_score"]
            >= MINIMUM_SCORE
            and job["match_category"]
            != "Ignore"
        )
    ]
