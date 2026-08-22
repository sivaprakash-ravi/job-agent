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


# ---------------------------------------------------------
# Advanced DevOps / SRE roles to reject
# ---------------------------------------------------------

ADVANCED_DEVOPS_TERMS = [
    "senior devops",
    "senior devops engineer",
    "lead devops",
    "devops lead",
    "principal devops",
    "principal devops engineer",
    "devops architect",
    "devops architecture",
    "l2 devops",
    "l3 devops",
    "l2/l3 devops",
    "l2 devops engineer",
    "l3 devops engineer",
    "senior sre",
    "senior site reliability",
    "lead sre",
    "lead site reliability",
    "principal sre",
    "principal site reliability",
    "sre architect",
    "sre lead",
    "l2 sre",
    "l3 sre",
]


# ---------------------------------------------------------
# General seniority terms
# ---------------------------------------------------------

ADVANCED_SENIORITY_TERMS = [
    "senior",
    "sr.",
    "sr ",
    "lead",
    "principal",
    "staff engineer",
    "staff software",
    "architect",
    "manager",
    "director",
    "head of",
]


# ---------------------------------------------------------
# L2 / L3 support rejection
#
# We specifically reject advanced support levels.
# Basic application/support roles remain allowed.
# ---------------------------------------------------------

ADVANCED_SUPPORT_TERMS = [
    "l2 support",
    "l3 support",
    "l2 application support",
    "l3 application support",
    "l2 production support",
    "l3 production support",
    "l2 technical support",
    "l3 technical support",
    "level 2 support",
    "level 3 support",
    "level ii support",
    "level iii support",
]


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
    """Combine useful job fields into searchable text."""

    fields = [
        job.get("title"),
        job.get("description"),
        job.get("skills"),
        job.get("category"),
        job.get("seniority"),
        job.get("job_type"),
        job.get("experience"),
        job.get("experience_requirement"),
        job.get("experience_years_min"),
        job.get("experience_years_max"),
    ]

    return normalise(fields)


def role_family(role):
    """Keep the meaningful part of a role title."""

    ignored_words = {
        "engineer",
        "engineering",
        "developer",
        "development",
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

    if not isinstance(enrichment, dict):
        enrichment = {}

    return (
        job.get(field_name)
        or enrichment.get(field_name)
    )


def matches_target_role(title, job_text, role):
    """Match target roles and sensible title variations."""

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

    # Allow role families such as DevOps/SRE
    # to match sensible title/description wording.
    if family in {
        "devops",
        "sre",
        "quality assurance",
        "qa",
        "testing",
        "test",
        "software tester",
    }:
        return (
            contains_phrase(
                title,
                family,
            )
            or contains_phrase(
                job_text,
                family,
            )
        )

    return False


def is_advanced_devops_role(title):
    """Reject explicitly advanced DevOps/SRE roles."""

    title_text = normalise(title)

    return any(
        contains_phrase(
            title_text,
            term,
        )
        for term in ADVANCED_DEVOPS_TERMS
    )


def is_advanced_support_role(title, job_text):
    """Reject clearly L2/L3 support positions."""

    text = normalise(
        f"{title} {job_text}"
    )

    return any(
        contains_phrase(
            text,
            term,
        )
        for term in ADVANCED_SUPPORT_TERMS
    )


def is_advanced_seniority_role(title):
    """
    Reject senior/lead/principal/architect roles.

    This is based primarily on the job title so that
    harmless mentions inside a description do not reject
    an otherwise suitable job.
    """

    title_text = normalise(title)

    return any(
        contains_phrase(
            title_text,
            term,
        )
        for term in ADVANCED_SENIORITY_TERMS
    )


def parse_experience_range(text):
    """
    Extract an experience requirement from text.

    Examples handled:

        2 years
        2+ years
        3 years
        3-5 years
        3 to 5 years
        1 - 2 years
        0-2 years
        minimum 3 years
        3 years of experience
        2+ years of experience

    Returns:
        (minimum_years, maximum_years)

    If only one number is present:
        2 years       -> (2, 2)
        2+ years      -> (2, None)
    """

    text = normalise(text)

    if not text:
        return None, None

    # Range:
    # 3-5 years
    # 3 - 5 years
    # 3 to 5 years
    range_pattern = re.search(
        r"(?<!\d)"
        r"(\d+(?:\.\d+)?)"
        r"\s*"
        r"(?:-|–|—|to)"
        r"\s*"
        r"(\d+(?:\.\d+)?)"
        r"\s*\+?"
        r"\s*"
        r"(?:years?|yrs?)"
        r"(?:\s+of\s+(?:professional\s+)?experience)?",
        text,
    )

    if range_pattern:
        minimum = float(
            range_pattern.group(1)
        )
        maximum = float(
            range_pattern.group(2)
        )

        return minimum, maximum

    # "2+ years"
    plus_pattern = re.search(
        r"(?<!\d)"
        r"(\d+(?:\.\d+)?)"
        r"\s*\+"
        r"\s*(?:years?|yrs?)"
        r"(?:\s+of\s+(?:professional\s+)?experience)?",
        text,
    )

    if plus_pattern:
        minimum = float(
            plus_pattern.group(1)
        )

        return minimum, None

    # "minimum 3 years"
    minimum_pattern = re.search(
        r"(?:minimum|at least)"
        r"\s+"
        r"(\d+(?:\.\d+)?)"
        r"\s*(?:years?|yrs?)"
        r"(?:\s+of\s+(?:professional\s+)?experience)?",
        text,
    )

    if minimum_pattern:
        minimum = float(
            minimum_pattern.group(1)
        )

        return minimum, None

    # "3 years of experience"
    experience_pattern = re.search(
        r"(?<!\d)"
        r"(\d+(?:\.\d+)?)"
        r"\s*(?:years?|yrs?)"
        r"\s+of\s+"
        r"(?:professional\s+)?"
        r"experience",
        text,
    )

    if experience_pattern:
        years = float(
            experience_pattern.group(1)
        )

        return years, years

    # "experience: 3 years"
    simple_pattern = re.search(
        r"(?:experience|exp)"
        r"\s*[:\-]?\s*"
        r"(\d+(?:\.\d+)?)"
        r"\s*(?:years?|yrs?)",
        text,
    )

    if simple_pattern:
        years = float(
            simple_pattern.group(1)
        )

        return years, years

    return None, None


def required_experience(job):
    """
    Find the strongest experience requirement.

    We inspect structured fields first and then the job
    description/title text.

    The highest detected requirement wins.

    This prevents:
        3-5 years
        3+ years

    from accidentally being interpreted as just "3".
    """

    candidates = []

    structured_fields = [
        "experience_years_min",
        "experience_years_max",
        "experience_requirement",
        "experience",
    ]

    for field_name in structured_fields:
        value = job_value(
            job,
            field_name,
        )

        if value is None:
            continue

        minimum, maximum = parse_experience_range(
            normalise(value)
        )

        if minimum is not None:
            candidates.append(
                (
                    minimum,
                    maximum,
                )
            )

    description = normalise(
        job.get("description")
    )

    if description:
        minimum, maximum = parse_experience_range(
            description
        )

        if minimum is not None:
            candidates.append(
                (
                    minimum,
                    maximum,
                )
            )

    title = normalise(
        job.get("title")
    )

    if title:
        minimum, maximum = parse_experience_range(
            title
        )

        if minimum is not None:
            candidates.append(
                (
                    minimum,
                    maximum,
                )
            )

    if not candidates:
        return None, None

    # Highest minimum requirement is the safest interpretation.
    highest_minimum = max(
        item[0]
        for item in candidates
    )

    maximum_values = [
        item[1]
        for item in candidates
        if item[1] is not None
    ]

    highest_maximum = (
        max(maximum_values)
        if maximum_values
        else None
    )

    return (
        highest_minimum,
        highest_maximum,
    )


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
    """Match preferred locations using common aliases."""

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
    """Score one job against the personal job profile."""

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

    # ---------------------------------------------------------
    # Experience
    # ---------------------------------------------------------

    required_min_years, required_max_years = (
        required_experience(job)
    )

    experience_score = 0

    if required_min_years is None:
        experience_note = (
            "No clear experience requirement found"
        )

    elif (
        required_min_years
        <= MAX_JOB_EXPERIENCE_YEARS
        and (
            required_max_years is None
            or required_max_years
            <= MAX_JOB_EXPERIENCE_YEARS
        )
    ):
        experience_score = 10

        if required_max_years is not None:
            experience_note = (
                f"Requires about "
                f"{required_min_years:g}-"
                f"{required_max_years:g} years: suitable"
            )
        else:
            experience_note = (
                f"Requires at least "
                f"{required_min_years:g} years: "
                f"within your limit"
            )

    else:
        experience_score = -50

        if required_max_years is not None:
            experience_note = (
                f"Requires about "
                f"{required_min_years:g}-"
                f"{required_max_years:g} years: "
                f"above your "
                f"{MAX_JOB_EXPERIENCE_YEARS:g}-year limit"
            )
        else:
            experience_note = (
                f"Requires at least "
                f"{required_min_years:g} years: "
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

    # ---------------------------------------------------------
    # HARD FILTER: Advanced DevOps/SRE
    # ---------------------------------------------------------

    if is_advanced_devops_role(
        title
    ):
        filter_reasons.append(
            "Advanced DevOps/SRE role"
        )

    # ---------------------------------------------------------
    # HARD FILTER: Advanced support level
    # ---------------------------------------------------------

    if is_advanced_support_role(
        title,
        job_text,
    ):
        filter_reasons.append(
            "L2/L3 support role"
        )

    # ---------------------------------------------------------
    # HARD FILTER: Seniority
    # ---------------------------------------------------------

    if is_advanced_seniority_role(
        title
    ):
        filter_reasons.append(
            "Senior/Lead/Principal/Architect role"
        )

    # ---------------------------------------------------------
    # Employment type
    # ---------------------------------------------------------

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

    # ---------------------------------------------------------
    # Location
    # ---------------------------------------------------------

    if not matched_locations:
        filter_reasons.append(
            "Outside preferred locations"
        )

    # ---------------------------------------------------------
    # HARD FILTER: Experience
    #
    # Any clearly stated requirement above 2 years
    # is rejected completely.
    # ---------------------------------------------------------

    if (
        required_min_years is not None
        and required_min_years
        > MAX_JOB_EXPERIENCE_YEARS
    ):
        filter_reasons.append(
            "Requires more than "
            f"{MAX_JOB_EXPERIENCE_YEARS:g} "
            "years of experience"
        )

    if (
        required_max_years is not None
        and required_max_years
        > MAX_JOB_EXPERIENCE_YEARS
    ):
        filter_reasons.append(
            "Experience range exceeds "
            f"{MAX_JOB_EXPERIENCE_YEARS:g} years"
        )

    # ---------------------------------------------------------
    # Role / skill relevance
    # ---------------------------------------------------------

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
        "required_experience_min": (
            required_min_years
        ),
        "required_experience_max": (
            required_max_years
        ),
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
    """Score every job and return best matches first."""

    ranked_jobs = [
        score_job(job)
        for job in jobs
    ]

    return sorted(
        ranked_jobs,
        key=lambda job: job["match_score"],
        reverse=True,
    )


def job_role_key(job):
    """
    Create a duplicate key using company + designation.

    The same designation at different companies is allowed.
    """

    company = normalise(
        job.get("company")
        or job.get("company_name")
    )

    title