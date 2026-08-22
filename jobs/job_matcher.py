"""Deep rule-based job matching for the daily job agent."""

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
    r"\bvp\b",
    r"\badvanced\b",
]


LEVEL_NUMBER_PATTERNS = [
    r"\bengineer\s*(?:ii|iii|iv|v|2|3|4|5)\b",
    r"\bqa\s*(?:ii|iii|iv|v|2|3|4|5)\b",
    r"\btester\s*(?:ii|iii|iv|v|2|3|4|5)\b",
    r"\banalyst\s*(?:ii|iii|iv|v|2|3|4|5)\b",
    r"\bspecialist\s*(?:ii|iii|iv|v|2|3|4|5)\b",
    r"\bdeveloper\s*(?:ii|iii|iv|v|2|3|4|5)\b",
]


ADVANCED_DOMAIN_TERMS = [
    "l2",
    "l3",
    "l2/l3",
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


EXPERIENCE_RANGE_PATTERN = re.compile(
    r"(\d+(?:\.\d+)?)"
    r"\s*(?:-|to)"
    r"\s*(\d+(?:\.\d+)?)"
    r"\s*(?:years?|yrs?)",
    re.IGNORECASE,
)


EXPERIENCE_PLUS_PATTERN = re.compile(
    r"(\d+(?:\.\d+)?)"
    r"\s*(?:\+|plus|or more|and above|and over)"
    r"\s*(?:years?|yrs?)",
    re.IGNORECASE,
)


EXPERIENCE_PATTERN = re.compile(
    r"(\d+(?:\.\d+)?)"
    r"\s*(?:years?|yrs?)"
    r"\s*(?:of\s+)?"
    r"(?:relevant\s+|professional\s+|hands-on\s+)?"
    r"experience",
    re.IGNORECASE,
)


REVERSE_EXPERIENCE_PATTERN = re.compile(
    r"experience"
    r"\s*(?:of|:)?\s*"
    r"(\d+(?:\.\d+)?)"
    r"\s*(?:years?|yrs?)",
    re.IGNORECASE,
)


TITLE_EXPERIENCE_PATTERN = re.compile(
    r"(\d+(?:\.\d+)?)"
    r"\s*(?:\+|plus)?"
    r"\s*(?:years?|yrs?)",
    re.IGNORECASE,
)


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
    text = normalise(value)

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


def contains_phrase(text, phrase):
    text = clean_text(text)
    phrase = clean_text(phrase)

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
    Search every field returned by the source.

    This intentionally includes all collected
    job details so experience requirements cannot
    hide in another field.
    """

    pieces = []

    for key, value in job.items():

        if key in {
            "match_score",
            "match_category",
            "match_details",
        }:
            continue

        pieces.append(
            f"{key}: {normalise(value)}"
        )

    return " ".join(pieces)


def has_advanced_title(title):
    text = clean_text(title)

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


def has_advanced_domain(title):
    text = clean_text(title)

    return any(
        contains_phrase(
            text,
            term,
        )
        for term in ADVANCED_DOMAIN_TERMS
    )


def title_experience_above_limit(title):
    """
    Detect experience directly in the designation.

    Examples:
        "Support Engineer 3 Yrs" -> reject
        "Support Engineer 3+ Years" -> reject
        "Support Engineer 2 Years" -> accept
    """

    title = clean_text(title)

    for match in TITLE_EXPERIENCE_PATTERN.finditer(
        title
    ):
        years = float(
            match.group(1)
        )

        matched_text = clean_text(
            match.group(0)
        )

        if (
            "+"
            in matched_text
            or "plus"
            in matched_text
        ):
            if years >= MAX_JOB_EXPERIENCE_YEARS:
                return True

        if years > MAX_JOB_EXPERIENCE_YEARS:
            return True

    return False


def extract_experience_requirements(text):
    """Extract all explicit experience requirements."""

    text = clean_text(text)

    results = []

    # 1-3 years / 1 to 3 years
    for match in EXPERIENCE_RANGE_PATTERN.finditer(
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

    # 3+ years / 3 or more years
    for match in EXPERIENCE_PLUS_PATTERN.finditer(
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

    # 3 years experience
    for match in EXPERIENCE_PATTERN.finditer(
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

    # experience of 3 years
    for match in REVERSE_EXPERIENCE_PATTERN.finditer(
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

    unique = []
    seen = set()

    for item in results:

        key = (
            item[0],
            item[1],
            item[2],
        )

        if key in seen:
            continue

        seen.add(key)
        unique.append(item)

    return unique


def analyse_experience(job):
    """
    Inspect the complete collected job.

    ANY explicit requirement above 2 years
    causes rejection.
    """

    complete_text = (
        get_complete_job_text(job)
    )

    title = clean_text(
        job.get("title")
    )

    requirements = (
        extract_experience_requirements(
            complete_text
        )
    )

    # Title-specific check.
    if title_experience_above_limit(
        title
    ):
        return {
            "found": True,
            "valid": False,
            "maximum_required": float("inf"),
            "requirements": [
                {
                    "text": title,
                    "reason": (
                        "Experience requirement "
                        "appears in title"
                    ),
                }
            ],
        }

    # No explicit experience found.
    if not requirements:
        return {
            "found": False,
            "valid": True,
            "maximum_required": None,
            "requirements": [],
        }

    maximum_required = 0

    for (
        minimum,
        maximum,
        matched,
    ) in requirements:

        if maximum == float("inf"):
            maximum_required = float("inf")
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
            for (
                minimum,
                maximum,
                matched,
            ) in requirements
        ],
    }


def matches_location(job):
    """
    Match actual preferred locations.

    Do NOT use TN / KA / TS abbreviations because
    they can represent US states.
    """

    location = clean_text(
        job.get("location")
    )

    work_mode = clean_text(
        job.get("work_mode")
        or job.get(
            "remote_work_model"
        )
    )

    # Remote
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

    # Indian locations
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


def role_matches(job):
    """Match genuine target-role titles."""

    title = clean_text(
        job.get("title")
    )

    matched_roles = []

    # Exact target role title matches.
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

    # Controlled role families.
    allowed_families = [
        "application support",
        "production support",
        "technical support",
        "cloud support",
        "cloud operations",
        "operations engineer",
        "production operations",
        "application operations",
        "technical operations",
        "qa engineer",
        "quality assurance",
        "software test",
        "test engineer",
        "qa analyst",
        "quality analyst",
        "manual tester",
        "software tester",
        "application tester",
        "devops engineer",
        "junior devops",
        "cloud engineer",
        "site reliability",
        "sre",
    ]

    for family in allowed_families:

        if contains_phrase(
            title,
            family,
        ):
            if family not in matched_roles:
                matched_roles.append(
                    family
                )

    return list(
        dict.fromkeys(
            matched_roles
        )
    )


def score_job(job):
    """Score and deeply filter one job."""

    title = clean_text(
        job.get("title")
    )

    complete_text = (
        get_complete_job_text(job)
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

    experience = analyse_experience(
        job
    )

    filter_reasons = []

    # Advanced designation.
    if has_advanced_title(
        title
    ):
        filter_reasons.append(
            "Advanced/senior-level designation"
        )

    # L2/L3 / advanced DevOps.
    if has_advanced_domain(
        title
    ):
        filter_reasons.append(
            "L2/L3 or advanced DevOps/SRE role"
        )

    # Experience.
    if not experience["valid"]:

        maximum = experience[
            "maximum_required"
        ]

        if maximum == float("inf"):
            display = "2+ years or higher"
        else:
            display = f"{maximum:g} years"

        filter_reasons.append(
            "Experience requirement exceeds "
            f"{MAX_JOB_EXPERIENCE_YEARS:g} years "
            f"({display})"
        )

    # Location.
    if not matches_location(job):
        filter_reasons.append(
            "Outside preferred locations"
        )

    # Employment.
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
        and EMPLOYMENT_TYPE == "full_time"
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

    # Genuine relevance.
    if (
        not matched_roles
        and len(matched_skills) < 4
    ):
        filter_reasons.append(
            "Insufficient role/skill relevance"
        )

    # Scoring.
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
        if matches_location(job)
        else 0
    )

    experience_score = (
        10
        if experience["valid"]
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

    result = dict(job)

    result["match_score"] = score

    if not passes:
        result["match_category"] = "Ignore"

    elif score >= 80:
        result["match_category"] = (
            "Excellent match"
        )

    elif score >= 65:
        result["match_category"] = (
            "Good match"
        )

    else:
        result["match_category"] = (
            "Possible match"
        )

    result["match_details"] = {
        "matched_roles": matched_roles,
        "matched_skills": matched_skills,
        "experience_analysis": experience,
        "filter_reasons": filter_reasons,
    }

    return result


def rank_jobs(jobs):
    """Rank all collected jobs."""

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


def normalize_company(value):
    text = clean_text(value)

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


def normalize_title(value):
    text = clean_text(value)

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


def duplicate_key(job):
    """
    Same company + same designation = duplicate.
    """

    company = normalize_company(
        job.get("company")
        or job.get(
            "company_name"
        )
    )

    title = normalize_title(
        job.get("title")
    )

    return (
        company,
        title,
    )


def keep_relevant_jobs(ranked_jobs):
    """
    Keep only jobs that pass all hard filters.

    Also remove duplicate company/designation
    combinations.
    """

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

        key = duplicate_key(job)

        if key in seen:
            continue

        seen.add(key)
        unique.append(job)

    return unique