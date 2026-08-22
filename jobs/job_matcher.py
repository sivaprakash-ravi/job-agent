"""Rule-based job matching for the daily job agent."""

import re
from datetime import datetime, timezone

from profile import (
    EMPLOYMENT_TYPE,
    LOCATIONS,
    MAX_JOB_EXPERIENCE_YEARS,
    SKILLS,
    TARGET_ROLES,
)


MINIMUM_SCORE = 45
MAX_JOB_AGE_DAYS = 7


LOCATION_ALIASES = {
    "Chennai": ["chennai", "tamil nadu", "tamilnadu", "tn"],
    "Bangalore": ["bangalore", "bengaluru", "karnataka", "ka"],
    "Hyderabad": ["hyderabad", "telangana", "ts"],
    "Coimbatore": ["coimbatore", "tamil nadu", "tamilnadu", "tn"],
    "Remote": ["remote", "work from home", "wfh", "anywhere"],
}


# Any of these in the JOB TITLE means the role is above
# the user's current target level.
ADVANCED_TITLE_TERMS = [
    "senior",
    "sr.",
    "sr ",
    "sr-",
    "sr_",
    "lead",
    "principal",
    "staff",
    "architect",
    "manager",
    "director",
    "head of",
    "vp ",
    "vice president",
    "avp",
]


ADVANCED_DEVOPS_TERMS = [
    "l2 devops",
    "l3 devops",
    "l2/l3 devops",
    "l2 sre",
    "l3 sre",
    "senior devops",
    "senior sre",
    "lead devops",
    "lead sre",
    "principal devops",
    "principal sre",
    "devops architect",
    "devops architecture",
    "sre architect",
    "sre lead",
    "site reliability architect",
    "site reliability lead",
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


def clean_text(value):
    """Normalize whitespace and punctuation spacing."""

    text = normalise(value)

    text = text.replace(
        "\u2013",
        "-",
    )
    text = text.replace(
        "\u2014",
        "-",
    )
    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


def contains_phrase(text, phrase):
    """Match a complete phrase."""

    text = clean_text(text)
    phrase = clean_text(phrase)

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
    """Combine all useful job fields."""

    fields = [
        job.get("title"),
        job.get("description"),
        job.get("skills"),
        job.get("category"),
        job.get("seniority"),
        job.get("job_type"),
        job.get("employment_type"),
        job.get("experience"),
        job.get("experience_requirement"),
    ]

    return normalise(fields)


def role_family(role):
    """Keep the meaningful part of a role."""

    ignored_words = {
        "engineer",
        "junior",
        "senior",
        "sr",
        "sr.",
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
    """Read a field including enrichment data."""

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
    """Match target roles."""

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


def has_advanced_title(title):
    """Reject senior/lead/architect/etc. titles."""

    title_text = clean_text(title)

    # Exact title-level words.
    patterns = [
        r"\bsenior\b",
        r"\bsr\.?\b",
        r"\blead\b",
        r"\bprincipal\b",
        r"\bstaff\b",
        r"\barchitect\b",
        r"\bmanager\b",
        r"\bdirector\b",
        r"\bhead\b",
        r"\bavp\b",
        r"\bvp\b",
        r"\bvice president\b",
    ]

    return any(
        re.search(
            pattern,
            title_text,
        )
        for pattern in patterns
    )


def is_advanced_devops_role(title):
    """Reject explicitly advanced DevOps/SRE roles."""

    title_text = clean_text(title)

    if has_advanced_title(title_text):
        # Advanced title wording is enough.
        if any(
            word in title_text
            for word in (
                "devops",
                "sre",
                "site reliability",
                "cloud",
                "operations",
            )
        ):
            return True

    return any(
        contains_phrase(
            title_text,
            term,
        )
        for term in ADVANCED_DEVOPS_TERMS
    )


def extract_experience_range(job):
    """
    Extract experience from structured fields AND description.

    Returns:
        (minimum_years, maximum_years)

    Examples:

        0-2 years      -> (0, 2)
        1-2 years      -> (1, 2)
        1-3 years      -> (1, 3)
        3+ years       -> (3, None)
        7-9 years      -> (7, 9)
        3 years        -> (3, 3)
        fresher        -> (0, 0)
    """

    structured_values = [
        job_value(
            job,
            "experience_years_min",
        ),
        job_value(
            job,
            "experience_requirement",
        ),
        job_value(
            job,
            "experience",
        ),
    ]

    description = normalise(
        job.get("description")
    )

    title = normalise(
        job.get("title")
    )

    combined = " ".join(
        str(value or "")
        for value in structured_values
    )

    combined = (
        combined
        + " "
        + description
        + " "
        + title
    )

    text = clean_text(
        combined
    )

    if not text:
        return None, None

    # ---------------------------------------------------------
    # Fresher / entry-level.
    # ---------------------------------------------------------

    if any(
        phrase in text
        for phrase in (
            "fresher",
            "freshers",
            "entry level",
            "entry-level",
        )
    ):
        return 0.0, 0.0

    # ---------------------------------------------------------
    # Explicit ranges.
    #
    # 1-3 years
    # 1 to 3 years
    # 1–3 years
    # ---------------------------------------------------------

    range_matches = re.findall(
        r"(\d+(?:\.\d+)?)"
        r"\s*(?:-|to)"
        r"\s*(\d+(?:\.\d+)?)"
        r"\s*(?:years?|yrs?)?",
        text,
    )

    if range_matches:

        ranges = []

        for minimum, maximum in range_matches:

            ranges.append(
                (
                    float(minimum),
                    float(maximum),
                )
            )

        # Use the most demanding range found.
        return max(
            ranges,
            key=lambda item: item[1],
        )

    # ---------------------------------------------------------
    # 3+ years / 2 or more years.
    # ---------------------------------------------------------

    plus_matches = re.findall(
        r"(\d+(?:\.\d+)?)"
        r"\s*(?:\+|or more|and above|and over)"
        r"\s*(?:years?|yrs?)?",
        text,
    )

    if plus_matches:

        values = [
            float(value)
            for value in plus_matches
        ]

        return max(values), None

    # ---------------------------------------------------------
    # Explicit "X years experience".
    # ---------------------------------------------------------

    experience_matches = re.findall(
        r"(\d+(?:\.\d+)?)"
        r"\s*(?:years?|yrs?)"
        r"(?:\s*(?:of)?\s*experience)?",
        text,
    )

    if experience_matches:

        values = [
            float(value)
            for value in experience_matches
        ]

        # Only use reasonably realistic experience numbers.
        # This prevents unrelated numbers such as years/dates
        # from becoming experience requirements.
        realistic = [
            value
            for value in values
            if 0 <= value <= 30
        ]

        if realistic:
            return (
                max(realistic),
                max(realistic),
            )

    return None, None


def required_experience(job):
    """
    Return the highest stated required experience.

    For 1-3 years -> 3.
    For 7-9 years -> 9.
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

    location_text = clean_text(
        location
    )

    work_mode_text = clean_text(
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
            matched.append(
                "Remote"
            )

        if any(
            alias_matches_location(
                location_text,
                alias,
            )
            for alias in LOCATION_ALIASES[
                "Remote"
            ]
        ):
            matched.append(
                "Remote"
            )

    return list(
        dict.fromkeys(matched)
    )


def parse_posted_date(job):
    """
    Try to parse a posted date.

    Returns a datetime or None.
    """

    value = (
        job.get("date_posted")
        or job.get("posted_at")
        or job.get("created_at")
    )

    if not value:
        return None

    text = clean_text(
        value
    )

    # Relative dates.
    relative_match = re.search(
        r"(\d+)\s*(hour|hours|day|days|week|weeks)\s*ago",
        text,
    )

    if relative_match:

        number = int(
            relative_match.group(1)
        )

        unit = (
            relative_match.group(2)
        )

        now = datetime.now(
            timezone.utc
        )

        if "hour" in unit:
            from datetime import timedelta

            return now - timedelta(
                hours=number
            )

        if "day" in unit:
            from datetime import timedelta

            return now - timedelta(
                days=number
            )

        if "week" in unit:
            from datetime import timedelta

            return now - timedelta(
                weeks=number
            )

    # ISO-style date.
    try:

        normalized = value.replace(
            "Z",
            "+00:00",
        )

        parsed = datetime.fromisoformat(
            normalized
        )

        if parsed.tzinfo is None:
            parsed = parsed.replace(
                tzinfo=timezone.utc
            )

        return parsed

    except Exception:
        pass

    # Common date formats.
    formats = [
        "%Y-%m-%d",
        "%Y-%m-%d %H:%M:%S",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%m/%d/%Y",
    ]

    for fmt in formats:

        try:

            parsed = datetime.strptime(
                value,
                fmt,
            )

            return parsed.replace(
                tzinfo=timezone.utc
            )

        except Exception:
            continue

    return None


def freshness_status(job):
    """
    Return:

        True  = definitely fresh
        False = definitely old
        None  = date unavailable
    """

    posted = parse_posted_date(
        job
    )

    if posted is None:
        return None

    now = datetime.now(
        timezone.utc
    )

    age_days = (
        now - posted
    ).total_seconds() / 86400

    return age_days <= MAX_JOB_AGE_DAYS


def category_for(score):

    if score >= 80:
        return "Excellent match"

    if score >= 65:
        return "Good match"

    if score >= MINIMUM_SCORE:
        return "Possible match"

    return "Ignore"


def score_job(job):
    """Score and hard-filter one job."""

    title = clean_text(
        job.get("title")
    )

    job_text = get_job_text(
        job
    )

    location = clean_text(
        job.get("location")
    )

    work_mode = clean_text(
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
    # Roles
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
    # Locations
    # ---------------------------------------------------------

    matched_locations = (
        matches_location(
            location,
            work_mode,
        )
    )

    # ---------------------------------------------------------
    # Experience
    # ---------------------------------------------------------

    minimum_years, maximum_years = (
        extract_experience_range(
            job
        )
    )

    required_years = (
        required_experience(
            job
        )
    )

    experience_score = 0

    if required_years is None:

        experience_score = 0

        experience_note = (
            "Experience requirement not found"
        )

    elif required_years <= MAX_JOB_EXPERIENCE_YEARS:

        experience_score = 10

        if (
            minimum_years is not None
            and maximum_years is not None
            and minimum_years
            != maximum_years
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
                "within limit"
            )

    else:

        experience_score = -20

        experience_note = (
            f"Requires "
            f"{required_years:g} years or "
            "more: above 2-year limit"
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
    # Employment
    # ---------------------------------------------------------

    employment_type = clean_text(
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

    # Senior/Lead/etc.
    if has_advanced_title(
        title
    ):
        filter_reasons.append(
            "Senior/Lead/Principal/"
            "Staff/Architect/Manager-level role"
        )

    # Advanced DevOps/SRE.
    if is_advanced_devops_role(
        title
    ):
        reason = (
            "Advanced DevOps/SRE role"
        )

        if reason not in filter_reasons:
            filter_reasons.append(
                reason
            )

    # Full-time.
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

    # Location.
    if not matched_locations:
        filter_reasons.append(
            "Outside preferred locations"
        )

    # ---------------------------------------------------------
    # HARD EXPERIENCE FILTER.
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
    # Relevance.
    # ---------------------------------------------------------

    if (
        not matched_roles
        and len(matched_skills) < 4
    ):
        filter_reasons.append(
            "Not enough target-role or "
            "skill overlap"
        )

    # ---------------------------------------------------------
    # Freshness.
    #
    # We reject jobs only when we can prove they
    # are older than the configured limit.
    #
    # Unknown date is kept because some portals
    # don't expose reliable dates.
    # ---------------------------------------------------------

    fresh = freshness_status(
        job
    )

    if fresh is False:

        filter_reasons.append(
            f"Job older than "
            f"{MAX_JOB_AGE_DAYS} days"
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
        "matched_roles": (
            matched_roles
        ),
        "matched_skills": (
            matched_skills
        ),
        "matched_locations": (
            matched_locations
        ),
        "experience_min_years": (
            minimum_years
        ),
        "experience_max_years": (
            maximum_years
        ),
        "experience_note": (
            experience_note
        ),
        "freshness": (
            "Fresh"
            if fresh is True
            else (
                "Old"
                if fresh is False
                else "Unknown"
            )
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


def normalize_company_name(company):
    """Normalize company names for deduplication."""

    company = clean_text(
        company
    )

    company = re.sub(
        r"\b(private limited|pvt ltd|pvt\. ltd\.|limited|ltd)\b",
        "",
        company,
    )

    company = re.sub(
        r"[^a-z0-9]+",
        " ",
        company,
    )

    return re.sub(
        r"\s+",
        " ",
        company,
    ).strip()


def normalize_title(title):
    """Normalize job titles for deduplication."""

    title = clean_text(
        title
    )

    # Remove common seniority terms so that
    # minor portal variations don't create duplicates.
    title = re.sub(
        r"\b(senior|sr\.?|lead|principal|staff|junior|jr\.?)\b",
        "",
        title,
    )

    # Remove punctuation.
    title = re.sub(
        r"[^a-z0-9]+",
        " ",
        title,
    )

    return re.sub(
        r"\s+",
        " ",
        title,
    ).strip()


def job_role_key(job):
    """
    Strong duplicate key.

    Company + normalized title + location.

    This prevents the same role appearing repeatedly
    from slightly different portal titles.
    """

    company = normalize_company_name(
        job.get("company")
        or job.get(
            "company_name"
        )
    )

    title = normalize_title(
        job.get("title")
    )

    location = clean_text(
        job.get("location")
    )

    return (
        company,
        title,
        location,
    )


def keep_relevant_jobs(ranked_jobs):
    """
    Keep only relevant jobs and remove duplicates.
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