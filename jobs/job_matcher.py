"""Deep rule-based job matching for the daily job agent."""

import re
from datetime import datetime, timezone, timedelta

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
    "Chennai": [
        "chennai",
        "tamil nadu",
        "tamilnadu",
    ],
    "Bangalore": [
        "bangalore",
        "bengaluru",
        "karnataka",
    ],
    "Hyderabad": [
        "hyderabad",
        "telangana",
    ],
    "Coimbatore": [
        "coimbatore",
    ],
    "Remote": [
        "remote",
        "work from home",
        "wfh",
        "anywhere",
    ],
}


# Hard reject title levels.
ADVANCED_TITLE_PATTERNS = [
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
    r"\bvice president\b",
    r"\bvp\b",
]


LEVEL_NUMBER_PATTERNS = [
    r"\bengineer\s*(?:ii|iii|iv|2|3|4)\b",
    r"\bqa\s*(?:ii|iii|iv|2|3|4)\b",
    r"\btester\s*(?:ii|iii|iv|2|3|4)\b",
    r"\banalyst\s*(?:ii|iii|iv|2|3|4)\b",
    r"\bspecialist\s*(?:ii|iii|iv|2|3|4)\b",
]


ADVANCED_DOMAIN_TERMS = [
    "l2",
    "l3",
    "level 2",
    "level 3",
    "senior devops",
    "lead devops",
    "principal devops",
    "devops architect",
    "senior sre",
    "lead sre",
    "principal sre",
    "sre architect",
    "site reliability lead",
    "site reliability architect",
]


def normalise(value):
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

    return str(
        value or ""
    ).lower()


def clean_text(value):
    text = normalise(
        value
    )

    text = (
        text
        .replace("\u2013", "-")
        .replace("\u2014", "-")
        .replace("\u2212", "-")
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


def contains_phrase(
    text,
    phrase,
):
    text = clean_text(
        text
    )

    phrase = clean_text(
        phrase
    )

    if not text or not phrase:
        return False

    return bool(
        re.search(
            r"(?<!\w)"
            + re.escape(phrase)
            + r"(?!\w)",
            text,
        )
    )


def get_complete_job_text(job):
    """
    IMPORTANT:
    Search EVERY field returned by the portal,
    not only description/title.
    """

    pieces = []

    for key, value in job.items():

        # Ignore internal matcher fields.
        if key in {
            "match_score",
            "match_category",
            "match_details",
        }:
            continue

        pieces.append(
            f"{key}: {normalise(value)}"
        )

    return " ".join(
        pieces
    )


def get_role_text(job):
    return " ".join(
        [
            normalise(
                job.get("title")
            ),
            normalise(
                job.get("description")
            ),
        ]
    )


def has_advanced_title(
    title
):
    text = clean_text(
        title
    )

    for pattern in ADVANCED_TITLE_PATTERNS:

        if re.search(
            pattern,
            text,
        ):
            return True

    for pattern in LEVEL_NUMBER_PATTERNS:

        if re.search(
            pattern,
            text,
        ):
            return True

    return False


def has_advanced_domain(
    complete_text
):
    text = clean_text(
        complete_text
    )

    return any(
        contains_phrase(
            text,
            term,
        )
        for term in ADVANCED_DOMAIN_TERMS
    )


def extract_experience_requirements(
    text
):
    """
    Find ALL explicit experience requirements
    throughout the complete listing.

    Returns a list of:
        (minimum, maximum, matched_text)

    The maximum requirement is used for hard filtering.
    """

    text = clean_text(
        text
    )

    results = []

    # ---------------------------------------------------------
    # Range:
    # 1-3 years
    # 1 to 3 years
    # 1–3 years
    # ---------------------------------------------------------

    range_pattern = re.compile(
        r"(\d+(?:\.\d+)?)"
        r"\s*(?:-|to)"
        r"\s*(\d+(?:\.\d+)?)"
        r"\s*(?:years?|yrs?)",
        re.IGNORECASE,
    )

    for match in range_pattern.finditer(
        text
    ):

        minimum = float(
            match.group(1)
        )

        maximum = float(
            match.group(2)
        )

        results.append(
            (
                minimum,
                maximum,
                match.group(0),
            )
        )

    # ---------------------------------------------------------
    # Plus:
    # 3+ years
    # 2 or more years
    # 5 years or more
    # ---------------------------------------------------------

    plus_pattern = re.compile(
        r"(\d+(?:\.\d+)?)"
        r"\s*(?:\+|or more|and above|and over)"
        r"\s*(?:years?|yrs?)",
        re.IGNORECASE,
    )

    for match in plus_pattern.finditer(
        text
    ):

        minimum = float(
            match.group(1)
        )

        results.append(
            (
                minimum,
                float("inf"),
                match.group(0),
            )
        )

    # ---------------------------------------------------------
    # Explicit experience wording.
    #
    # "3 years of experience"
    # "minimum 3 years experience"
    # "3 years experience required"
    # ---------------------------------------------------------

    explicit_pattern = re.compile(
        r"(\d+(?:\.\d+)?)"
        r"\s*(?:years?|yrs?)"
        r"\s*(?:of\s+)?"
        r"(?:relevant\s+|professional\s+|hands-on\s+)?"
        r"experience",
        re.IGNORECASE,
    )

    for match in explicit_pattern.finditer(
        text
    ):

        years = float(
            match.group(1)
        )

        results.append(
            (
                years,
                years,
                match.group(0),
            )
        )

    # ---------------------------------------------------------
    # "experience of 3 years"
    # ---------------------------------------------------------

    reverse_pattern = re.compile(
        r"experience"
        r"\s*(?:of|:)?\s*"
        r"(\d+(?:\.\d+)?)"
        r"\s*(?:years?|yrs?)",
        re.IGNORECASE,
    )

    for match in reverse_pattern.finditer(
        text
    ):

        years = float(
            match.group(1)
        )

        results.append(
            (
                years,
                years,
                match.group(0),
            )
        )

    # Remove duplicate matches.
    unique = []

    seen = set()

    for item in results:

        key = (
            item[0],
            item[1],
            item[2],
        )

        if key not in seen:

            seen.add(key)
            unique.append(item)

    return unique


def analyse_experience(
    job
):
    """
    Deep experience analysis.

    The COMPLETE job listing is inspected.

    Any explicit requirement above 2 years
    causes rejection.
    """

    complete_text = (
        get_complete_job_text(
            job
        )
    )

    requirements = (
        extract_experience_requirements(
            complete_text
        )
    )

    if not requirements:

        return {
            "found": False,
            "valid": True,
            "maximum_required": None,
            "requirements": [],
        }

    maximum_required = 0

    for minimum, maximum, matched in requirements:

        if maximum == float("inf"):
            maximum_required = float(
                "inf"
            )

        else:
            maximum_required = max(
                maximum_required,
                maximum,
            )

    valid = (
        maximum_required
        <= MAX_JOB_EXPERIENCE_YEARS
    )

    return {
        "found": True,
        "valid": valid,
        "maximum_required": (
            maximum_required
        ),
        "requirements": [
            {
                "minimum": minimum,
                "maximum": (
                    None
                    if maximum == float("inf")
                    else maximum
                ),
                "text": matched,
            }
            for minimum, maximum, matched
            in requirements
        ],
    }


def matches_location(
    job
):
    location = clean_text(
        job.get("location")
    )

    work_mode = clean_text(
        job.get("work_mode")
        or job.get(
            "remote_work_model"
        )
    )

    # Remote.
    if "Remote" in LOCATIONS:

        if any(
            contains_phrase(
                location,
                alias,
            )
            for alias in LOCATION_ALIASES[
                "Remote"
            ]
        ):
            return True

        if any(
            contains_phrase(
                work_mode,
                alias,
            )
            for alias in LOCATION_ALIASES[
                "Remote"
            ]
        ):
            return True

    for preferred in LOCATIONS:

        if preferred == "Remote":
            continue

        aliases = LOCATION_ALIASES.get(
            preferred,
            [preferred],
        )

        if any(
            contains_phrase(
                location,
                alias,
            )
            for alias in aliases
        ):
            return True

    return False


def role_matches(
    job
):
    title = clean_text(
        job.get("title")
    )

    complete_text = (
        get_complete_job_text(
            job
        )
    )

    matched_roles = []

    for role in TARGET_ROLES:

        role_clean = clean_text(
            role
        )

        if contains_phrase(
            title,
            role_clean,
        ):

            matched_roles.append(
                role
            )
            continue

        # Only allow broader matching for
        # genuinely relevant families.
        family = (
            role_clean
            .replace(
                " engineer",
                "",
            )
            .strip()
        )

        if (
            family
            and len(family) >= 4
            and contains_phrase(
                title,
                family,
            )
        ):

            matched_roles.append(
                role
            )

    # DevOps/SRE/Cloud can match complete text,
    # but not generic unrelated roles.
    for family in (
        "devops",
        "sre",
        "site reliability",
        "cloud support",
        "cloud operations",
    ):

        if contains_phrase(
            complete_text,
            family,
        ):

            for role in TARGET_ROLES:

                if family in clean_text(
                    role
                ):

                    if role not in matched_roles:
                        matched_roles.append(
                            role
                        )

    return list(
        dict.fromkeys(
            matched_roles
        )
    )


def score_job(
    job
):
    title = clean_text(
        job.get("title")
    )

    complete_text = (
        get_complete_job_text(
            job
        )
    )

    matched_roles = role_matches(
        job
    )

    matched_skills = [
        skill
        for skill in SKILLS
        if contains_phrase(
            complete_text,
            skill,
        )
    ]

    experience = (
        analyse_experience(
            job
        )
    )

    filter_reasons = []

    # ---------------------------------------------------------
    # Seniority.
    # ---------------------------------------------------------

    if has_advanced_title(
        title
    ):

        filter_reasons.append(
            "Advanced title level"
        )

    # ---------------------------------------------------------
    # Advanced DevOps/SRE.
    # ---------------------------------------------------------

    if has_advanced_domain(
        title
    ):

        filter_reasons.append(
            "L2/L3 or advanced DevOps/SRE role"
        )

    # ---------------------------------------------------------
    # Experience.
    # ---------------------------------------------------------

    if not experience[
        "valid"
    ]:

        maximum = (
            experience[
                "maximum_required"
            ]
        )

        if maximum == float(
            "inf"
        ):

            display = "2+ years or more"

        else:

            display = (
                f"{maximum:g} years"
            )

        filter_reasons.append(
            "Experience requirement exceeds "
            f"{MAX_JOB_EXPERIENCE_YEARS:g} years "
            f"({display})"
        )

    # ---------------------------------------------------------
    # Location.
    # ---------------------------------------------------------

    if not matches_location(
        job
    ):

        filter_reasons.append(
            "Outside preferred locations"
        )

    # ---------------------------------------------------------
    # Employment.
    # ---------------------------------------------------------

    employment = clean_text(
        job.get(
            "employment_type"
        )
        or job.get(
            "job_type"
        )
    )

    if (
        employment
        and EMPLOYMENT_TYPE
        == "full_time"
        and not any(
            value in employment
            for value in (
                "full-time",
                "full time",
                "fulltime",
            )
        )
    ):

        filter_reasons.append(
            "Not full-time"
        )

    # ---------------------------------------------------------
    # Relevance.
    # ---------------------------------------------------------

    if (
        not matched_roles
        and len(matched_skills) < 4
    ):

        filter_reasons.append(
            "Insufficient role/skill relevance"
        )

    # ---------------------------------------------------------
    # Score.
    # ---------------------------------------------------------

    role_score = min(
        35,
        len(matched_roles)
        * 35,
    )

    skill_score = min(
        40,
        len(matched_skills)
        * 4,
    )

    location_score = (
        15
        if matches_location(
            job
        )
        else 0
    )

    experience_score = (
        10
        if experience[
            "valid"
        ]
        else -30
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

    passes = not filter_reasons

    result = dict(
        job
    )

    result[
        "match_score"
    ] = score

    result[
        "match_category"
    ] = (
        "Excellent match"
        if passes and score >= 80
        else (
            "Good match"
            if passes and score >= 65
            else (
                "Possible match"
                if passes
                else "Ignore"
            )
        )
    )

    result[
        "match_details"
    ] = {
        "matched_roles": matched_roles,
        "matched_skills": matched_skills,
        "experience_analysis": experience,
        "filter_reasons": filter_reasons,
    }

    return result


def rank_jobs(
    jobs
):
    ranked = [
        score_job(job)
        for job in jobs
    ]

    return sorted(
        ranked,
        key=lambda job: job.get(
            "match_score",
            0,
        ),
        reverse=True,
    )


def normalize_company(
    value
):
    text = clean_text(
        value
    )

    text = re.sub(
        r"\b(private limited|pvt ltd|pvt\. ltd\.|limited|ltd)\b",
        "",
        text,
    )

    return re.sub(
        r"\s+",
        " ",
        text,
    ).strip()


def normalize_title(
    value
):
    text = clean_text(
        value
    )

    text = re.sub(
        r"[^a-z0-9]+",
        " ",
        text,
    )

    return re.sub(
        r"\s+",
        " ",
        text,
    ).strip()


def duplicate_key(
    job
):
    return (
        normalize_company(
            job.get(
                "company"
            )
            or job.get(
                "company_name"
            )
        ),
        normalize_title(
            job.get(
                "title"
            )
        ),
        clean_text(
            job.get(
                "location"
            )
        ),
    )


def keep_relevant_jobs(
    ranked_jobs
):
    relevant = [
        job
        for job in ranked_jobs
        if job.get(
            "match_category"
        ) != "Ignore"
    ]

    unique = []
    seen = set()

    for job in relevant:

        key = duplicate_key(
            job
        )

        if key in seen:
            continue

        seen.add(key)
        unique.append(job)

    return unique