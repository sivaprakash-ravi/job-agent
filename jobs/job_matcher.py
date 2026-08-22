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


# Explicitly advanced DevOps / SRE roles.
# These are rejected because the user's current DevOps
# experience is basic.
ADVANCED_DEVOPS_TERMS = [
    "senior devops",
    "senior devops engineer",
    "lead devops",
    "lead devops engineer",
    "principal devops",
    "principal devops engineer",
    "devops architect",
    "devops architecture",
    "devops lead",
    "l2 devops",
    "l3 devops",
    "l2/l3 devops",
    "senior sre",
    "senior site reliability",
    "lead sre",
    "principal sre",
    "sre architect",
    "sre lead",
    "site reliability lead",
    "site reliability architect",
]


def normalise(value):
    """Convert values into lowercase searchable text."""

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
    """Match a complete phrase."""

    text = normalise(text)
    phrase = normalise(phrase).strip()

    if not text or not phrase:
        return False

    pattern = (
        r"(?<!\w)"
        + re.escape(phrase)
        + r"(?!\w)"
    )

    return bool(
        re.search(
            pattern,
            text,
        )
    )


def get_job_text(job):
    """Combine useful job fields."""

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
    """Keep the meaningful part of a role title."""

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

    enrichment = job.get(
        "enrichment",
        {},
    )

    if not isinstance(
        enrichment,
        dict,
    ):
        enrichment = {}

    return (
        job.get(field_name)
        or enrichment.get(field_name)
    )


def matches_target_role(
    title,
    job_text,
    role,
):
    """Match target roles and sensible variations."""

    family = role_family(role)

    if contains_phrase(
        title,
        role,
    ):
        return True

    if family and contains_phrase(
        title,
        family,
    ):
        return True

    if family in {
        "devops",
        "sre",
        "site reliability",
    }:
        return contains_phrase(
            job_text,
            family,
        )

    return False


def is_advanced_devops_role(title):
    """Reject explicitly advanced DevOps/SRE titles."""

    title_text = normalise(title)

    return any(
        contains_phrase(
            title_text,
            term,
        )
        for term in ADVANCED_DEVOPS_TERMS
    )


def extract_experience_range(job):
    """
    Extract the experience requirement.

    Returns:
        (minimum_years, maximum_years)

    Examples:

        "0-2 years"       -> (0, 2)
        "1-3 years"       -> (1, 3)
        "2+ years"        -> (2, None)
        "3 years"         -> (3, 3)
        "fresher"         -> (0, 0)
    """

    value = job_value(
        job,
        "experience_years_min",
    )

    if value is None:
        value = (
            job.get(
                "experience_requirement"
            )
            or job.get(
                "experience"
            )
            or ""
        )

    text = normalise(value)

    if not text:
        return None, None

    # Fresher / entry-level wording.
    if any(
        phrase in text
        for phrase in (
            "fresher",
            "freshers",
            "entry level",
            "entry-level",
            "0 year",
            "0 years",
        )
    ):
        return 0.0, 0.0

    # Range such as:
    # 1-3 years
    # 1 to 3 years
    # 1–3 years
    range_match = re.search(
        r"(\d+(?:\.\d+)?)"
        r"\s*(?:-|–|—|\bto\b)"
        r"\s*(\d+(?:\.\d+)?)",
        text,
    )

    if range_match:
        minimum = float(
            range_match.group(1)
        )
        maximum = float(
            range_match.group(2)
        )

        return minimum, maximum

    # "3+ years", "2 or more years"
    plus_match = re.search(
        r"(\d+(?:\.\d+)?)"
        r"\s*(?:\+|or more|and above|and over)",
        text,
    )

    if plus_match:
        minimum = float(
            plus_match.group(1)
        )

        return minimum, None

    # Single requirement such as:
    # "2 years experience"
    single_match = re.search(
        r"(\d+(?:\.\d+)?)",
        text,
    )

    if single_match:
        years = float(
            single_match.group(1)
        )

        return years, years

    return None, None


def required_experience(job):
    """
    Return the highest stated required experience.

    For a range such as 1-3 years, return 3.
    This is important because the hard limit is <= 2.
    """

    minimum, maximum = (
        extract_experience_range(job)
    )

    if maximum is not None:
        return maximum

    return minimum


def alias_matches_location(
    location_text,
    alias,
):
    """Safely match location aliases."""

    alias = alias.lower().strip()

    if alias in {
        "tn",
        "ka",
        "ts",
    }:
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


def matches_location(
    location,
    work_mode,
):
    """Match preferred locations."""

    location_text = normalise(
        location
    )

    work_mode_text = normalise(
        work_mode
    )

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
            matched.append(
                preferred_location
            )

    if "Remote" in LOCATIONS:

        if any(
            alias_matches_location(
                work_mode_text,
                alias,
            )
            for alias in LOCATION_ALIASES[
                "Remote"
            ]
        ):
            matched.append("Remote")

        if any(
            alias_matches_location(
                location_text,
                alias,
            )
            for alias in LOCATION_ALIASES[
                "Remote"
            ]
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
    """Score one job against the personal profile."""

    title = normalise(
        job.get("title")
    )

    job_text = get_job_text(
        job
    )

    location = normalise(
        job.get("location")
    )

    work_mode = normalise(
        job.get("work_mode")
        or job.get(
            "remote_work_model"
        )
        or (
            "remote"
            if job.get(
                "is_remote"
            )
            else ""
        )
    )

    # ---------------------------------------------------------
    # Target roles
    # ---------------------------------------------------------

    matched_roles = [
        role
        for role in TARGET_ROLES
        if matches_target_role(
            title,
            job_text,
            role,
        )
    ]

    # ---------------------------------------------------------
    # Skills
    # ---------------------------------------------------------

    matched_skills = [
        skill
        for skill in SKILLS
        if contains_phrase(
            job_text,
            skill,
        )
    ]

    # ---------------------------------------------------------
    # Location
    # ---------------------------------------------------------

    matched_locations = matches_location(
        location,
        work_mode,
    )

    # ---------------------------------------------------------
    # Experience
    # ---------------------------------------------------------

    minimum_years, maximum_years = (
        extract_experience_range(job)
    )

    required_years = required_experience(
        job
    )

    experience_score = 0

    if required_years is None:

        experience_score = 5

        experience_note = (
            "No experience requirement found"
        )

    elif required_years <= MAX_JOB_EXPERIENCE_YEARS:

        experience_score = 10

        if (
            minimum_years is not None
            and maximum_years is not None
            and minimum_years != maximum_years
        ):
            experience_note = (
                f"Requires "
                f"{minimum_years:g}-"
                f"{maximum_years:g} years: "
                "within limit"
            )
        else:
            experience_note = (
                f"Requires about "
                f"{required_years:g} years: "
                "suitable"
            )

    else:

        experience_score = -20

        experience_note = (
            f"Requires up to/about "
            f"{required_years:g} years: "
            f"above your "
            f"{MAX_JOB_EXPERIENCE_YEARS:g}-year limit"
        )

    # ---------------------------------------------------------
    # Score
    # ---------------------------------------------------------

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

    # ---------------------------------------------------------
    # Employment type
    # ---------------------------------------------------------

    employment_type = normalise(
        job_value(
            job,
            "employment_type",
        )
        or job.get(
            "job_type"
        )
    )

    # ---------------------------------------------------------
    # Hard filters
    # ---------------------------------------------------------

    filter_reasons = []

    # Advanced DevOps/SRE.
    if is_advanced_devops_role(
        title
    ):
        filter_reasons.append(
            "Advanced DevOps/SRE role"
        )

    # Full-time only.
    if employment_type:

        if (
            EMPLOYMENT_TYPE
            == "full_time"
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

    # Preferred location only.
    if not matched_locations:
        filter_reasons.append(
            "Outside preferred locations"
        )

    # ---------------------------------------------------------
    # HARD EXPERIENCE LIMIT
    #
    # Anything whose maximum stated requirement
    # is above 2 years is rejected.
    #
    # Examples:
    # 1-3 years -> REJECT
    # 2-4 years -> REJECT
    # 3+ years  -> REJECT
    # 3 years   -> REJECT
    # 0-2 years -> ACCEPT
    # 1-2 years -> ACCEPT
    # 2 years   -> ACCEPT
    # ---------------------------------------------------------

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

    # ---------------------------------------------------------
    # Role/skill relevance.
    # ---------------------------------------------------------

    if (
        not matched_roles
        and len(matched_skills) < 4
    ):
        filter_reasons.append(
            "Not enough target-role or "
            "skill overlap"
        )

    passes_filters = (
        not filter_reasons
    )

    ranked_job = dict(job)

    ranked_job[
        "match_score"
    ] = score

    ranked_job[
        "match_category"
    ] = (
        category_for(score)
        if passes_filters
        else "Ignore"
    )

    ranked_job[
        "match_details"
    ] = {
        "matched_roles": matched_roles,
        "matched_skills": matched_skills,
        "matched_locations": matched_locations,
        "experience_min_years": (
            minimum_years
        ),
        "experience_max_years": (
            maximum_years
        ),
        "experience_note": (
            experience_note
        ),
        "employment_type": (
            employment_type
            or "Not listed"
        ),
        "work_mode": (
            work_mode
            or "Not listed"
        ),
        "filter_reasons": (
            filter_reasons
        ),
    }

    return ranked_job


def rank_jobs(jobs):
    """Score every job and return best matches first."""

    ranked_jobs = [
        score_job(job)
        for job in jobs
    ]

    return sorted(
        ranked_jobs,
        key=lambda job: job[
            "match_score"
        ],
        reverse=True,
    )


def job_role_key(job):
    """
    Strict duplicate key:

    company + designation

    Same designation at different companies
    is allowed.

    Same company + same designation is
    considered a duplicate.
    """

    company = normalise(
        job.get("company")
        or job.get(
            "company_name"
        )
    )

    title = normalise(
        job.get("title")
    )

    company = re.sub(
        r"\s+",
        " ",
        company,
    ).strip()

    title = re.sub(
        r"\s+",
        " ",
        title,
    ).strip()

    return (
        company,
        title,
    )


def keep_relevant_jobs(ranked_jobs):
    """
    Keep only jobs that pass all hard filters.

    Also strictly remove duplicate
    company + designation combinations.
    """

    relevant_jobs = [
        job
        for job in ranked_jobs
        if (
            job.get(
                "match_score",
                0,
            )
            >= MINIMUM_SCORE
            and job.get(
                "match_category"
            )
            != "Ignore"
        )
    ]

    unique_jobs = []

    seen_roles = set()

    for job in relevant_jobs:

        key = job_role_key(
            job
        )

        if key in seen_roles:
            continue

        seen_roles.add(
            key
        )

        unique_jobs.append(
            job
        )

    return unique_jobs