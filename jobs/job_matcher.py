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
    "Chennai": ["chennai", "tamil nadu", "tamilnadu", "tn"],
    "Bangalore": ["bangalore", "bengaluru", "karnataka", "ka"],
    "Hyderabad": ["hyderabad", "telangana", "ts"],
    "Coimbatore": ["coimbatore", "tamil nadu", "tamilnadu", "tn"],
    "Remote": ["remote", "work from home", "wfh", "anywhere"],
}


# Clearly advanced titles.
# We do NOT reject "Engineer III" or similar automatically.
# Actual experience requirements are checked separately.
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
    Recursively collect every textual value from
    the complete job object.

    This is important because experience may exist
    in metadata, enrichment, JSON-LD, description,
    seniority, requirements, or nested fields.
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
                (
                    prefix.lower(),
                    text,
                )
            )

    return values


def get_all_job_text(job):
    """Return the complete job record as searchable text."""

    return normalise(job)


def get_job_text(job):
    """Combine the most useful job fields."""

    fields = [
        job.get("title"),
        job.get("description"),
        job.get("skills"),
        job.get("category"),
        job.get("seniority"),
        job.get("job_type"),
        job.get("employment_type"),
        job.get("location"),
        job.get("work_mode"),
        job.get("remote_work_model"),
        job.get("experience"),
        job.get("experience_requirement"),
        job.get("experience_years"),
        job.get("experience_years_min"),
        job.get("experience_years_max"),
        job.get("full_job_page_text"),
        job.get("job_page_json_ld_text"),
    ]

    return normalise(fields)


def role_family(role):
    """Keep the meaningful part of a role."""

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
    """Read direct or enrichment fields."""

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


def matches_target_role(title, job_text, role):
    """Match target role variations."""

    family = role_family(role)

    if contains_phrase(title, role):
        return True

    if family and contains_phrase(title, family):
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
    """Detect clearly advanced titles."""

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
    Extract explicit experience requirements.

    Examples:

        0-2 years
        1-3 years
        2+ years
        3 years
        3 to 5 years
        minimum 3 years
        at least 3 years
        3 years of experience
        experience: 3 years
    """

    text = normalise(text)

    results = []

    if not text:
        return results

    # ---------------------------------------------------------
    # RANGES
    # ---------------------------------------------------------

    for match in re.finditer(
        r"(\d+(?:\.\d+)?)"
        r"\s*(?:-|–|—|\bto\b)"
        r"\s*(\d+(?:\.\d+)?)"
        r"\s*(?:years?|yrs?)?",
        text,
    ):

        results.append(
            (
                float(match.group(1)),
                float(match.group(2)),
                match.group(0),
            )
        )

    # ---------------------------------------------------------
    # 3+ / 3 OR MORE / 3 AND ABOVE
    # ---------------------------------------------------------

    for match in re.finditer(
        r"(\d+(?:\.\d+)?)"
        r"\s*(?:\+|or more|and above|and over)"
        r"\s*(?:years?|yrs?)?",
        text,
    ):

        results.append(
            (
                float(match.group(1)),
                None,
                match.group(0),
            )
        )

    # ---------------------------------------------------------
    # MINIMUM / AT LEAST
    # ---------------------------------------------------------

    for match in re.finditer(
        r"(?:minimum|at least)"
        r"(?:\s+of)?\s+"
        r"(\d+(?:\.\d+)?)"
        r"\s*(?:years?|yrs?)",
        text,
    ):

        results.append(
            (
                float(match.group(1)),
                None,
                match.group(0),
            )
        )

    # ---------------------------------------------------------
    # 3 YEARS OF EXPERIENCE
    # ---------------------------------------------------------

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

    # ---------------------------------------------------------
    # EXPERIENCE: 3 YEARS
    # ---------------------------------------------------------

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
    Scan every textual field in the complete job record.
    """

    findings = []
    seen = set()

    for field_name, text in flatten_job_values(job):

        detected = extract_experience_numbers(text)

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
    Determine the highest explicit experience requirement.

    Example:

        1-2 years + 3 years mentioned elsewhere
        -> highest requirement = 3

    This prevents a hidden 6-year requirement from
    being ignored just because another field says 1-2.
    """

    findings = extract_all_experience_requirements(job)

    if not findings:
        return None, None, []

    highest = None

    for finding in findings:

        maximum = finding["maximum"]

        if maximum is None:
            maximum = finding["minimum"]

        if maximum is None:
            continue

        if (
            highest is None
            or maximum > highest["value"]
        ):

            highest = {
                "value": maximum,
                "finding": finding,
            }

    if highest is None:
        return None, None, findings

    return (
        highest["value"],
        highest["finding"],
        findings,
    )


def required_experience(job):
    """Backward-compatible helper."""

    required, _, _ = get_required_experience(job)

    return required


def alias_matches_location(location_text, alias):
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


def matches_location(location, work_mode):
    """Match preferred locations."""

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

            matched.append(
                preferred_location
            )

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


def get_verification_status(job):
    """Determine whether job details were successfully fetched."""

    verification = job.get(
        "detail_verification",
        {},
    )

    if isinstance(
        verification,
        dict,
    ):

        if verification.get("success"):
            return "VERIFIED"

    explicit = normalise(
        job.get(
            "verification_status"
        )
    )

    if explicit == "verified":
        return "VERIFIED"

    return "UNVERIFIED"


def score_job(job):
    """Score and strictly validate one job."""

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
        or job.get("remote_work_model")
        or (
            "remote"
            if job.get("is_remote")
            else ""
        )
    )

    verification_status = get_verification_status(
        job
    )

    # ---------------------------------------------------------
    # TARGET ROLE
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
        highest_finding,
        experience_findings,
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
            highest_finding["field"]
            if highest_finding
            else "job details"
        )

        matched_text = (
            highest_finding["text"]
            if highest_finding
            else ""
        )

        experience_note = (
            f"Rejected: "
            f"{required_years:g}+ years "
            f"in {field_name} "
            f"({matched_text})"
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
    # EMPLOYMENT
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

    # ---------------------------------------------------------
    # EXPERIENCE HARD LIMIT
    #
    # This is ALWAYS enforced when an explicit
    # requirement above 2 years is found.
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
    # UNVERIFIED EXPERIENCE
    #
    # If the page could not be fetched AND there is
    # no experience information anywhere in the source
    # data, don't send it to Telegram.
    #
    # If source metadata already contains <=2 years,
    # it can continue even if the page is unavailable.
    # ---------------------------------------------------------

    elif (
        verification_status == "UNVERIFIED"
        and required_years is None
    ):

        filter_reasons.append(
            "Experience could not be verified "
            "from available job data"
        )

    # ---------------------------------------------------------
    # ADVANCED TITLE
    # ---------------------------------------------------------

    if is_advanced_role(title):

        filter_reasons.append(
            "Advanced/senior role"
        )

    # ---------------------------------------------------------
    # FULL TIME
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
    # LOCATION
    # ---------------------------------------------------------

    if not matched_locations:

        filter_reasons.append(
            "Outside preferred locations"
        )

    # ---------------------------------------------------------
    # ROLE / SKILL RELEVANCE
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
    # FINAL
    # ---------------------------------------------------------

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

        "verification_status": verification_status,

        "experience_years_detected": required_years,

        "experience_note": experience_note,

        "experience_findings": experience_findings,

        "employment_type": (
            employment_type
            or "Not listed"
        ),

        "work_mode": (
            work_mode
            or "Not listed"
        ),

        "filter_reasons": filter_reasons,

        "full_record_scanned": True,

        "full_record_text_available": bool(
            all_job_text
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
        key=lambda job: job.get(
            "match_score",
            0,
        ),
        reverse=True,
    )


def job_role_key(job):
    """Duplicate key = company + designation."""

    company = normalise(
        job.get("company")
        or job.get("company_name")
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
    """Keep only jobs that pass all hard filters."""

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

        key = job_role_key(job)

        if key in seen_roles:
            continue

        seen_roles.add(key)

        unique_jobs.append(job)

    return unique_jobs


def get_rejected_jobs(ranked_jobs):
    """Return rejected jobs for audit reports."""

    return [
        job
        for job in ranked_jobs
        if job.get(
            "match_category"
        ) == "Ignore"
    ]
