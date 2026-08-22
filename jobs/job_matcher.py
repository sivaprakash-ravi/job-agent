"""Strict rule-based job matching for the daily job agent."""

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


ADVANCED_ROLE_TERMS = [
    "senior devops",
    "sr devops",
    "lead devops",
    "principal devops",
    "devops architect",
    "devops lead",
    "senior sre",
    "sr sre",
    "lead sre",
    "principal sre",
    "sre architect",
    "sre lead",
    "site reliability lead",
    "site reliability architect",
    "senior site reliability engineer",
    "principal site reliability engineer",
    "lead site reliability engineer",
    "senior software engineer",
    "sr software engineer",
    "lead software engineer",
    "principal software engineer",
    "staff software engineer",
    "senior test engineer",
    "sr test engineer",
    "lead test engineer",
    "principal test engineer",
    "senior qa",
    "sr qa",
    "lead qa",
    "principal qa",
]


EXPERIENCE_FIELD_NAMES = {
    "experience",
    "experience_years",
    "experience_years_min",
    "experience_years_max",
    "experience_requirement",
    "experience_required",
    "required_experience",
    "minimum_experience",
    "maximum_experience",
    "years_of_experience",
    "required_years",
    "minimum_years",
    "maximum_years",
    "qualification",
    "qualifications",
    "requirements",
    "job_requirements",
    "requirements_text",
    "job_description",
    "description",
    "responsibilities",
    "preferred_qualifications",
    "basic_qualifications",
}


def normalise(value):
    """Convert any value into lowercase searchable text."""

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
        re.search(pattern, text)
    )


def flatten_job_values(value, prefix=""):
    """
    Recursively collect all text values from a job.

    This allows the matcher to inspect nested enrichment,
    requirements, qualifications and other provider fields.
    """

    values = []

    if isinstance(value, dict):
        for key, item in value.items():
            child_prefix = (
                f"{prefix}.{key}"
                if prefix
                else str(key)
            )

            values.extend(
                flatten_job_values(
                    item,
                    child_prefix,
                )
            )

    elif isinstance(value, list):
        for index, item in enumerate(value):
            child_prefix = (
                f"{prefix}[{index}]"
            )

            values.extend(
                flatten_job_values(
                    item,
                    child_prefix,
                )
            )

    else:
        text = normalise(value)

        if text:
            values.append(
                (prefix.lower(), text)
            )

    return values


def get_all_job_text(job):
    """Return the complete searchable text from the job."""

    return normalise(job)


def get_job_text(job):
    """Combine important job fields."""

    fields = [
        job.get("title"),
        job.get("description"),
        job.get("skills"),
        job.get("category"),
        job.get("seniority"),
        job.get("job_type"),
        job.get("employment_type"),
        job.get("location"),
    ]

    return normalise(fields)


def role_family(role):
    """Keep the meaningful part of a role title."""

    ignored_words = {
        "engineer",
        "junior",
        "senior",
        "sr",
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


def is_advanced_role(title):
    """Reject explicitly senior/lead/principal roles."""

    title_text = normalise(title)

    return any(
        contains_phrase(
            title_text,
            term,
        )
        for term in ADVANCED_ROLE_TERMS
    )


def extract_experience_numbers(text):
    """
    Extract experience requirements from text.

    Handles:
        0-2 years
        1-3 years
        2+ years
        3 years
        3 to 5 years
        3 years of experience
        minimum 3 years
        3+ years experience
    """

    text = normalise(text)

    results = []

    if not text:
        return results

    # Ranges: 1-3, 1 to 3, 1–3
    for match in re.finditer(
        r"(\d+(?:\.\d+)?)"
        r"\s*(?:-|–|—|\bto\b)"
        r"\s*(\d+(?:\.\d+)?)"
        r"\s*(?:years?|yrs?)?",
        text,
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
    for match in re.finditer(
        r"(\d+(?:\.\d+)?)"
        r"\s*(?:\+|or more|and above|and over)"
        r"\s*(?:years?|yrs?)?",
        text,
    ):
        minimum = float(
            match.group(1)
        )

        results.append(
            (
                minimum,
                None,
                match.group(0),
            )
        )

    # "minimum of 3 years"
    for match in re.finditer(
        r"(?:minimum|at least)"
        r"(?:\s+of)?\s+"
        r"(\d+(?:\.\d+)?)"
        r"\s*(?:years?|yrs?)",
        text,
    ):
        minimum = float(
            match.group(1)
        )

        results.append(
            (
                minimum,
                None,
                match.group(0),
            )
        )

    # "3 years of experience"
    for match in re.finditer(
        r"(\d+(?:\.\d+)?)"
        r"\s*(?:years?|yrs?)"
        r"(?:\s+of)?\s+experience",
        text,
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

    # "experience: 3 years"
    for match in re.finditer(
        r"experience"
        r"(?:\s*[:\-])\s*"
        r"(\d+(?:\.\d+)?)"
        r"\s*(?:years?|yrs?)",
        text,
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

    return results


def extract_all_experience_requirements(job):
    """
    Scan the complete job object.

    Returns every detected experience requirement.
    """

    flattened = flatten_job_values(job)

    findings = []

    seen = set()

    for field_name, text in flattened:

        detected = extract_experience_numbers(
            text
        )

        for minimum, maximum, matched_text in detected:

            key = (
                field_name,
                minimum,
                maximum,
                matched_text,
            )

            if key in seen:
                continue

            seen.add(key)

            findings.append(
                {
                    "field": field_name,
                    "minimum": minimum,
                    "maximum": maximum,
                    "text": matched_text,
                }
            )

    return findings


def get_required_experience(job):
    """
    Determine the strictest experience requirement
    found anywhere in the job.

    If ANY job detail requires more than 2 years,
    the job is rejected.

    Example:

        title: Junior QA
        description: 1-2 years
        requirements: 3+ years

    Result:
        REJECT
    """

    findings = extract_all_experience_requirements(
        job
    )

    if not findings:
        return None, None, []

    highest_requirement = 0.0
    highest_finding = None

    for finding in findings:

        maximum = finding["maximum"]

        if maximum is None:
            maximum = finding["minimum"]

        if maximum is None:
            continue

        if maximum > highest_requirement:
            highest_requirement = maximum
            highest_finding = finding

    if highest_finding is None:
        return None, None, findings

    return (
        highest_requirement,
        highest_finding,
        findings,
    )


def required_experience(job):
    """Backward-compatible experience helper."""

    required, _, _ = get_required_experience(
        job
    )

    return required


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

    all_job_text = get_all_job_text(
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
    # TARGET ROLES
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
    # SKILLS
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
    # LOCATION
    # ---------------------------------------------------------

    matched_locations = matches_location(
        location,
        work_mode,
    )

    # ---------------------------------------------------------
    # EXPERIENCE
    # ---------------------------------------------------------

    (
        required_years,
        highest_experience_finding,
        all_experience_findings,
    ) = get_required_experience(
        job
    )

    if required_years is None:

        experience_score = 5

        experience_note = (
            "No explicit experience requirement found"
        )

    elif required_years <= MAX_JOB_EXPERIENCE_YEARS:

        experience_score = 10

        experience_note = (
            f"Highest detected requirement: "
            f"{required_years:g} years"
        )

    else:

        experience_score = -30

        field_name = (
            highest_experience_finding[
                "field"
            ]
            if highest_experience_finding
            else "job details"
        )

        matched_text = (
            highest_experience_finding[
                "text"
            ]
            if highest_experience_finding
            else ""
        )

        experience_note = (
            f"Rejected: detected "
            f"{required_years:g}+ years "
            f"in {field_name}"
            f" ({matched_text})"
        )

    # ---------------------------------------------------------
    # SCORE
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
    # EMPLOYMENT TYPE
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
    # HARD FILTERS
    # ---------------------------------------------------------

    filter_reasons = []

    # Advanced / senior roles.
    if is_advanced_role(
        title
    ):
        filter_reasons.append(
            "Advanced/senior role"
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

    # Location.
    if not matched_locations:
        filter_reasons.append(
            "Outside preferred locations"
        )

    # ---------------------------------------------------------
    # STRICT EXPERIENCE FILTER
    # ---------------------------------------------------------

    if (
        required_years is not None
        and required_years
        > MAX_JOB_EXPERIENCE_YEARS
    ):

        filter_reasons.append(
            "Experience requirement exceeds "
            f"{MAX_JOB_EXPERIENCE_YEARS:g} years"
        )

    # ---------------------------------------------------------
    # ROLE RELEVANCE
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
        "matched_roles": (
            matched_roles
        ),
        "matched_skills": (
            matched_skills
        ),
        "matched_locations": (
            matched_locations
        ),
        "experience_years_detected": (
            required_years
        ),
        "experience_note": (
            experience_note
        ),
        "experience_findings": (
            all_experience_findings
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
        "full_record_scanned": True,
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
        key=lambda job: job.get(
            "match_score",
            0,
        ),
        reverse=True,
    )


def job_role_key(job):
    """Create duplicate key using company + title."""

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
    Keep only jobs that pass every hard filter.

    Also remove duplicate company + designation.
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


def get_rejected_jobs(ranked_jobs):
    """
    Return every rejected job.

    This is used by collect_jobs.py to create
    reports/rejected_jobs.json for inspection.
    """

    return [
        job
        for job in ranked_jobs
        if job.get(
            "match_category"
        ) == "Ignore"
    ]