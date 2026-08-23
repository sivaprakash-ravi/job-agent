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


# ============================================================
# LOCATION
# ============================================================

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


# ============================================================
# ADVANCED / SENIOR TITLE FILTERS
# ============================================================

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


# ============================================================
# EXPERIENCE PATTERNS
# ============================================================

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


# ============================================================
# EXPERIENCE-SAFE CONTENT FIELDS
#
# IMPORTANT:
# Do NOT scan arbitrary metadata such as:
# date_posted
# posted_at
# company size
# employee count
# IDs
# URLs
# salary
# ratings
# source metadata
#
# Full job page text is allowed because it contains the
# actual public job description/details.
# ============================================================

EXPERIENCE_CONTENT_FIELDS = {
    "title",
    "description",
    "full_job_page_text",
    "job_description",
    "experience",
    "experience_range",
    "experience_requirement",
    "experience_required",
    "experience_years",
    "experience_years_min",
    "experience_years_max",
    "required_experience",
    "minimum_experience",
    "maximum_experience",
    "years_of_experience",
    "required_years",
    "minimum_years",
    "maximum_years",
    "requirements",
    "requirements_text",
    "job_requirements",
    "qualifications",
    "qualification",
    "basic_qualifications",
    "preferred_qualifications",
}


# ============================================================
# GENERAL TEXT HELPERS
# ============================================================

def normalise(value):
    """Convert nested values into searchable lowercase text."""

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
    """Normalize searchable text."""

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
    """Match a complete phrase."""

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


# ============================================================
# JOB CONTENT
# ============================================================

def get_job_content_text(job):
    """
    Return meaningful job-content fields for role/skill matching.

    Metadata such as dates, IDs, URLs and company statistics
    are intentionally excluded.
    """

    pieces = []

    allowed_fields = {
        "title",
        "description",
        "full_job_page_text",
        "job_description",
        "experience",
        "experience_range",
        "experience_requirement",
        "experience_required",
        "experience_years",
        "experience_years_min",
        "experience_years_max",
        "required_experience",
        "minimum_experience",
        "maximum_experience",
        "years_of_experience",
        "required_years",
        "minimum_years",
        "maximum_years",
        "requirements",
        "requirements_text",
        "job_requirements",
        "qualifications",
        "qualification",
        "basic_qualifications",
        "preferred_qualifications",
        "skills",
        "category",
    }

    for key, value in job.items():

        key_name = str(
            key
        ).lower().strip()

        if key_name not in allowed_fields:
            continue

        if value is None:
            continue

        pieces.append(
            normalise(value)
        )

    return " ".join(pieces)


def get_complete_job_text(job):
    """
    Backward-compatible helper.

    Returns meaningful searchable job content rather than
    blindly scanning every metadata field.
    """

    return get_job_content_text(job)


# ============================================================
# ADVANCED ROLE CHECKS
# ============================================================

def has_advanced_title(title):
    """Reject explicitly senior/advanced designations."""

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
    """Reject explicitly advanced DevOps/SRE designations."""

    text = clean_text(title)

    return any(
        contains_phrase(
            text,
            term,
        )
        for term in ADVANCED_DOMAIN_TERMS
    )


# ============================================================
# TITLE EXPERIENCE
# ============================================================

def title_experience_above_limit(title):
    """
    Detect explicit experience in the title.

    Examples:

        Support Engineer 3 Yrs
            -> reject

        Support Engineer 3+ Years
            -> reject

        Support Engineer 2 Years
            -> accept

        Support Engineer 2+ Years
            -> reject
            because 2+ includes experience above 2.
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

            if (
                years
                >= MAX_JOB_EXPERIENCE_YEARS
            ):
                return True

        if (
            years
            > MAX_JOB_EXPERIENCE_YEARS
        ):
            return True

    return False


# ============================================================
# EXPERIENCE EXTRACTION
# ============================================================

def extract_experience_requirements(text):
    """Extract explicit experience requirements from job content."""

    text = clean_text(text)

    results = []

    # --------------------------------------------------------
    # 1-3 years
    # 1 to 3 years
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # 3+ years
    # 3 or more years
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # 3 years experience
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # experience of 3 years
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Deduplicate
    # --------------------------------------------------------

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

        seen.add(
            key
        )

        unique.append(
            item
        )

    return unique


# ============================================================
# DEEP EXPERIENCE ANALYSIS
# ============================================================

def analyse_experience(job):
    """
    Inspect genuine job-content fields for experience.

    IMPORTANT:
    Metadata such as date_posted, company size, IDs,
    URLs and source fields are NOT scanned.

    ANY explicit experience requirement above the user's
    maximum is rejected.

    Examples:

        0-2 years  -> ACCEPT
        1-2 years  -> ACCEPT
        2 years    -> ACCEPT
        1-3 years  -> REJECT
        2-4 years  -> REJECT
        3+ years   -> REJECT
        6+ years   -> REJECT
    """

    title = clean_text(
        job.get("title")
    )

    # --------------------------------------------------------
    # TITLE CHECK
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # COLLECT ONLY REAL JOB-CONTENT FIELDS
    # --------------------------------------------------------

    texts = []

    seen_text = set()

    for key, value in job.items():

        key_name = str(
            key
        ).lower().strip()

        if (
            key_name
            not in EXPERIENCE_CONTENT_FIELDS
        ):
            continue

        if value is None:
            continue

        text = clean_text(
            value
        )

        if not text:
            continue

        if text in seen_text:
            continue

        seen_text.add(
            text
        )

        texts.append(
            (
                key_name,
                text,
            )
        )

    # --------------------------------------------------------
    # EXTRACT REQUIREMENTS
    # --------------------------------------------------------

    requirements = []

    seen_requirements = set()

    for field_name, text in texts:

        detected = (
            extract_experience_requirements(
                text
            )
        )

        for (
            minimum,
            maximum,
            matched,
        ) in detected:

            key = (
                field_name,
                minimum,
                maximum,
                matched,
            )

            if key in seen_requirements:
                continue

            seen_requirements.add(
                key
            )

            requirements.append(
                {
                    "field": field_name,
                    "minimum": minimum,
                    "maximum": (
                        None
                        if maximum == float("inf")
                        else maximum
                    ),
                    "text": matched,
                }
            )

    # --------------------------------------------------------
    # NO EXPLICIT EXPERIENCE FOUND
    # --------------------------------------------------------

    if not requirements:

        return {
            "found": False,
            "valid": True,
            "maximum_required": None,
            "requirements": [],
        }

    # --------------------------------------------------------
    # FIND HIGHEST REQUIREMENT
    # --------------------------------------------------------

    maximum_required = 0

    for requirement in requirements:

        maximum = requirement[
            "maximum"
        ]

        if maximum is None:

            maximum_required = float(
                "inf"
            )

            continue

        maximum_required = max(
            maximum_required,
            maximum,
        )

    # --------------------------------------------------------
    # HARD EXPERIENCE LIMIT
    # --------------------------------------------------------

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
        "requirements": requirements,
    }


# ============================================================
# LOCATION
# ============================================================

def matches_location(job):
    """
    Match preferred locations.

    Do NOT use TN / KA / TS abbreviations because they can
    represent US states and create false matches.
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

    # --------------------------------------------------------
    # Remote
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Indian preferred locations
    # --------------------------------------------------------

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


# ============================================================
# ROLE MATCHING
# ============================================================

def role_matches(job):
    """Match genuine target-role titles."""

    title = clean_text(
        job.get("title")
    )

    matched_roles = []

    # --------------------------------------------------------
    # Exact target-role title matches
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Controlled role families
    # --------------------------------------------------------

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


# ============================================================
# SCORING + FILTERING
# ============================================================

def score_job(job):
    """Score and deeply filter one job."""

    title = clean_text(
        job.get("title")
    )

    job_content = (
        get_job_content_text(job)
    )

    matched_roles = role_matches(
        job
    )

    matched_skills = [
        skill
        for skill in SKILLS
        if contains_phrase(
            job_content,
            skill,
        )
    ]

    experience = analyse_experience(
        job
    )

    filter_reasons = []

    # --------------------------------------------------------
    # SENIOR / ADVANCED TITLE
    # --------------------------------------------------------

    if has_advanced_title(
        title
    ):

        filter_reasons.append(
            "Advanced/senior-level designation"
        )

    # --------------------------------------------------------
    # ADVANCED DEVOPS / SRE
    # --------------------------------------------------------

    if has_advanced_domain(
        title
    ):

        filter_reasons.append(
            "Advanced DevOps/SRE designation"
        )

    # --------------------------------------------------------
    # EXPERIENCE
    # --------------------------------------------------------

    if not experience["valid"]:

        maximum = experience[
            "maximum_required"
        ]

        if maximum == float("inf"):

            display = (
                "2+ years or higher"
            )

        else:

            display = (
                f"{maximum:g} years"
            )

        filter_reasons.append(
            "Experience requirement exceeds "
            f"{MAX_JOB_EXPERIENCE_YEARS:g} years "
            f"({display})"
        )

    # --------------------------------------------------------
    # LOCATION
    # --------------------------------------------------------

    if not matches_location(
        job
    ):

        filter_reasons.append(
            "Outside preferred locations"
        )

    # --------------------------------------------------------
    # EMPLOYMENT TYPE
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # ROLE / SKILL RELEVANCE
    # --------------------------------------------------------

    if (
        not matched_roles
        and len(matched_skills) < 4
    ):

        filter_reasons.append(
            "Insufficient role/skill relevance"
        )

    # --------------------------------------------------------
    # SCORING
    # --------------------------------------------------------

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

    result[
        "match_score"
    ] = score

    if not passes:

        result[
            "match_category"
        ] = "Ignore"

    elif score >= 80:

        result[
            "match_category"
        ] = "Excellent match"

    elif score >= 65:

        result[
            "match_category"
        ] = "Good match"

    else:

        result[
            "match_category"
        ] = "Possible match"

    result[
        "match_details"
    ] = {
        "matched_roles": matched_roles,
        "matched_skills": matched_skills,
        "experience_analysis": experience,
        "filter_reasons": filter_reasons,
    }

    return result


# ============================================================
# RANKING
# ============================================================

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


# ============================================================
# DUPLICATE HANDLING
# ============================================================

def normalize_company(value):
    """Normalize company names for duplicate detection."""

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


def normalize_title(value):
    """Normalize titles for duplicate detection."""

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


# ============================================================
# FINAL ELIGIBLE JOBS
# ============================================================

def keep_relevant_jobs(ranked_jobs):
    """
    Keep only jobs that pass all hard filters.

    Also remove duplicate company/designation combinations.
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

        key = duplicate_key(
            job
        )

        if key in seen:
            continue

        seen.add(
            key
        )

        unique.append(
            job
        )

    return unique


# ============================================================
# REJECTED JOBS
# ============================================================

def get_rejected_jobs(ranked_jobs):
    """
    Return all jobs rejected by the hard filters.

    These jobs are retained for the rejected_jobs.json
    audit report so we can inspect exactly why they failed.
    """

    return [
        job
        for job in ranked_jobs
        if job.get(
            "match_category"
        ) == "Ignore"
    ]
