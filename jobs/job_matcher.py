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
# SENIORITY METADATA
# ============================================================

SENIORITY_FIELDS = {
    "seniority",
    "seniority_level",
    "senioritylevel",
    "experience_level",
    "experiencelevel",
    "career_level",
    "careerlevel",
    "level",
    "job_level",
    "joblevel",
}


ADVANCED_SENIORITY_PATTERNS = [
    r"\bmid[\s-]*senior\b",
    r"\bsenior\b",
    r"\bsr\.?\b",
    r"\blead\b",
    r"\bprincipal\b",
    r"\bstaff\b",
    r"\bmanager\b",
    r"\bdirector\b",
    r"\bhead\b",
    r"\bexecutive\b",
    r"\bavp\b",
    r"\bvp\b",
]


# ============================================================
# EXPERIENCE CONTENT FIELDS
#
# ONLY these fields are allowed to participate in experience
# analysis. Arbitrary metadata is deliberately ignored.
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


# Nested containers which may legitimately contain job content.
EXPERIENCE_CONTAINER_FIELDS = {
    "job",
    "details",
    "content",
    "description",
    "requirements",
    "qualifications",
    "enrichment",
    "data",
}


# ============================================================
# EXPERIENCE REGEX PATTERNS
# ============================================================

# 3-5 years
# 3 - 5 years
# 3 to 5 years
# 3–5 years
EXPERIENCE_RANGE_PATTERN = re.compile(
    r"\b(\d+(?:\.\d+)?)"
    r"\s*(?:-|to|–|—)"
    r"\s*(\d+(?:\.\d+)?)"
    r"\s*(?:years?|yrs?)\b",
    re.IGNORECASE,
)


# 3+
# 3+ years
# 3 plus years
# 3 or more years
# 3 years or more
# 3 years and above
# 3 years and over
EXPERIENCE_PLUS_PATTERN = re.compile(
    r"\b(\d+(?:\.\d+)?)"
    r"\s*(?:\+|plus)"
    r"\s*(?:years?|yrs?)?\b"
    r"|"
    r"\b(\d+(?:\.\d+)?)"
    r"\s*(?:years?|yrs?)"
    r"\s*(?:or\s+more|and\s+above|and\s+over)\b",
    re.IGNORECASE,
)


# minimum 4 years
# minimum of 4 years
# minimum 4 yrs
# minimum of 4 yrs
# required 4 years
# requires 4 years
# required minimum of 4 years
MINIMUM_EXPERIENCE_PATTERN = re.compile(
    r"\b(?:"
    r"minimum"
    r"|minimum\s+of"
    r"|required"
    r"|requires"
    r"|required\s+minimum"
    r"|required\s+minimum\s+of"
    r")"
    r"\s*"
    r"(\d+(?:\.\d+)?)"
    r"\s*(?:years?|yrs?)\b",
    re.IGNORECASE,
)


# at least 4 years
# at least 4 yrs
AT_LEAST_EXPERIENCE_PATTERN = re.compile(
    r"\bat\s+least\s+"
    r"(\d+(?:\.\d+)?)"
    r"\s*(?:years?|yrs?)\b",
    re.IGNORECASE,
)


# must have 4 years
# must possess 4 years
# should have 4 years
# candidates should have 4 years
# applicants must have 4 years
# candidates must possess 4 years
MUST_HAVE_EXPERIENCE_PATTERN = re.compile(
    r"\b(?:"
    r"must\s+have"
    r"|must\s+possess"
    r"|should\s+have"
    r"|should\s+possess"
    r"|candidates?\s+must\s+have"
    r"|candidates?\s+must\s+possess"
    r"|candidates?\s+should\s+have"
    r"|candidates?\s+should\s+possess"
    r"|applicants?\s+must\s+have"
    r"|applicants?\s+must\s+possess"
    r")"
    r"\s+"
    r"(\d+(?:\.\d+)?)"
    r"\s*(?:years?|yrs?)\b",
    re.IGNORECASE,
)


# 4 years of experience
# 4 years of related experience
# 4 years of relevant experience
# 4 years professional experience
# 4 years hands-on experience
# 4 years technical experience
# 4 years industry experience
# 4 years software testing experience
#
# Broad intentionally, because actual JDs use many variations.
DIRECT_EXPERIENCE_PATTERN = re.compile(
    r"\b(\d+(?:\.\d+)?)"
    r"\s*(?:years?|yrs?)"
    r"\s*(?:"
    r"of\s+"
    r")?"
    r"(?:"
    r"[a-z][a-z0-9/&,\-]*"
    r"\s+"
    r"){0,8}"
    r"experience\b",
    re.IGNORECASE,
)


# experience of 4 years
# experience: 4 years
REVERSE_EXPERIENCE_PATTERN = re.compile(
    r"\bexperience"
    r"\s*(?:of|:)?\s*"
    r"(\d+(?:\.\d+)?)"
    r"\s*(?:years?|yrs?)\b",
    re.IGNORECASE,
)


# 4 years required
# 4 years are required
# 4 years is required
YEARS_REQUIRED_PATTERN = re.compile(
    r"\b(\d+(?:\.\d+)?)"
    r"\s*(?:years?|yrs?)"
    r"\s*(?:"
    r"are\s+required"
    r"|is\s+required"
    r"|required"
    r")\b",
    re.IGNORECASE,
)


# Title-only experience:
# QA Engineer 3 Years
# Support Engineer 3+
TITLE_EXPERIENCE_PATTERN = re.compile(
    r"\b(\d+(?:\.\d+)?)"
    r"\s*(?:\+|plus)?"
    r"\s*(?:years?|yrs?)\b",
    re.IGNORECASE,
)


# ============================================================
# GENERAL HELPERS
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
        .replace("\u2012", "-")
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
    Return meaningful job-content fields.

    Metadata such as:
    - dates
    - IDs
    - URLs
    - salary
    - company statistics
    - source metadata

    is intentionally excluded.
    """

    pieces = []

    allowed_fields = (
        EXPERIENCE_CONTENT_FIELDS
        | {
            "skills",
            "category",
        }
    )

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

    return " ".join(
        pieces
    )


def get_complete_job_text(job):
    """Backward-compatible helper."""

    return get_job_content_text(
        job
    )


# ============================================================
# RECURSIVE EXPERIENCE CONTENT EXTRACTION
# ============================================================

def extract_experience_content(
    value,
    field_name="",
):
    """
    Recursively collect text ONLY from legitimate job-content
    structures.

    This prevents metadata numbers from becoming fake
    experience requirements.
    """

    texts = []

    if isinstance(value, dict):

        for key, item in value.items():

            key_name = str(
                key
            ).lower().strip()

            if key_name in EXPERIENCE_CONTENT_FIELDS:

                texts.extend(
                    extract_experience_content(
                        item,
                        key_name,
                    )
                )

            elif key_name in EXPERIENCE_CONTAINER_FIELDS:

                texts.extend(
                    extract_experience_content(
                        item,
                        key_name,
                    )
                )

        return texts

    if isinstance(value, list):

        for item in value:

            texts.extend(
                extract_experience_content(
                    item,
                    field_name,
                )
            )

        return texts

    text = clean_text(
        value
    )

    if text:

        texts.append(
            (
                field_name,
                text,
            )
        )

    return texts


# ============================================================
# SENIORITY
# ============================================================

def has_advanced_seniority(job):
    """
    Check explicit seniority metadata.

    Reject:
        Mid-Senior
        Senior
        Sr.
        Lead
        Principal
        Staff
        Manager
        Director
        Head
        VP

    Do not reject merely because a job is:
        Associate
        Junior
        Entry Level
    """

    for key, value in job.items():

        key_name = str(
            key
        ).lower().strip()

        if key_name not in SENIORITY_FIELDS:
            continue

        text = clean_text(
            value
        )

        if not text:
            continue

        for pattern in ADVANCED_SENIORITY_PATTERNS:

            if re.search(
                pattern,
                text,
            ):
                return True

    return False


def has_advanced_title(title):
    """Reject explicitly senior/advanced titles."""

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


def has_advanced_domain(title):
    """Reject explicitly advanced DevOps/SRE titles."""

    text = clean_text(
        title
    )

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
    """Reject explicit >2-year requirements in job titles."""

    title = clean_text(
        title
    )

    for match in TITLE_EXPERIENCE_PATTERN.finditer(
        title
    ):

        years = float(
            match.group(1)
        )

        matched = clean_text(
            match.group(0)
        )

        if (
            "+"
            in matched
            or "plus"
            in matched
        ):

            if (
                years
                >= MAX_JOB_EXPERIENCE_YEARS
            ):
                return True

        elif (
            years
            > MAX_JOB_EXPERIENCE_YEARS
        ):

            return True

    return False


# ============================================================
# EXPERIENCE EXTRACTION
# ============================================================

def extract_experience_requirements(text):
    """
    Detect many real-world experience expressions.

    Returns tuples:

        minimum,
        maximum,
        matched_text,
        requirement_type

    requirement_type is:
        mandatory
        preferred
        general
    """

    text = clean_text(
        text
    )

    results = []

    def add(
        minimum,
        maximum,
        matched,
        requirement_type="mandatory",
    ):

        results.append(
            (
                minimum,
                maximum,
                clean_text(matched),
                requirement_type,
            )
        )

    # --------------------------------------------------------
    # RANGE
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

        add(
            minimum,
            maximum,
            match.group(0),
        )

    # --------------------------------------------------------
    # PLUS
    # --------------------------------------------------------

    for match in EXPERIENCE_PLUS_PATTERN.finditer(
        text
    ):

        first = match.group(1)
        second = match.group(2)

        years = float(
            first
            if first is not None
            else second
        )

        add(
            years,
            float("inf"),
            match.group(0),
        )

    # --------------------------------------------------------
    # MINIMUM / REQUIRED
    # --------------------------------------------------------

    for match in MINIMUM_EXPERIENCE_PATTERN.finditer(
        text
    ):

        years = float(
            match.group(1)
        )

        add(
            years,
            years,
            match.group(0),
        )

    # --------------------------------------------------------
    # AT LEAST
    # --------------------------------------------------------

    for match in AT_LEAST_EXPERIENCE_PATTERN.finditer(
        text
    ):

        years = float(
            match.group(1)
        )

        add(
            years,
            years,
            match.group(0),
        )

    # --------------------------------------------------------
    # MUST / SHOULD HAVE
    # --------------------------------------------------------

    for match in MUST_HAVE_EXPERIENCE_PATTERN.finditer(
        text
    ):

        years = float(
            match.group(1)
        )

        add(
            years,
            years,
            match.group(0),
        )

    # --------------------------------------------------------
    # YEARS REQUIRED
    # --------------------------------------------------------

    for match in YEARS_REQUIRED_PATTERN.finditer(
        text
    ):

        years = float(
            match.group(1)
        )

        add(
            years,
            years,
            match.group(0),
        )

    # --------------------------------------------------------
    # DIRECT EXPERIENCE
    # --------------------------------------------------------

    for match in DIRECT_EXPERIENCE_PATTERN.finditer(
        text
    ):

        years = float(
            match.group(1)
        )

        add(
            years,
            years,
            match.group(0),
        )

    # --------------------------------------------------------
    # REVERSE
    # --------------------------------------------------------

    for match in REVERSE_EXPERIENCE_PATTERN.finditer(
        text
    ):

        years = float(
            match.group(1)
        )

        add(
            years,
            years,
            match.group(0),
        )

    # --------------------------------------------------------
    # PREFERRED CLASSIFICATION
    #
    # We keep preferred experience visible, but it is not
    # automatically treated as a hard requirement.
    # --------------------------------------------------------

    preferred_markers = [
        "preferred",
        "preferably",
        "nice to have",
        "nice-to-have",
        "desired",
        "bonus",
        "plus",
        "good to have",
    ]

    classified = []

    for (
        minimum,
        maximum,
        matched,
        requirement_type,
    ) in results:

        # Find a local sentence around the match.
        index = text.find(
            matched
        )

        context = ""

        if index >= 0:

            start = max(
                0,
                index - 100,
            )

            end = min(
                len(text),
                index + len(matched) + 100,
            )

            context = text[
                start:end
            ]

        if any(
            marker in context
            for marker in preferred_markers
        ):

            requirement_type = "preferred"

        classified.append(
            (
                minimum,
                maximum,
                matched,
                requirement_type,
            )
        )

    # --------------------------------------------------------
    # DEDUPLICATE
    # --------------------------------------------------------

    unique = []

    seen = set()

    for item in classified:

        key = (
            item[0],
            item[1],
            item[2],
            item[3],
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
    Perform deep experience analysis across the complete
    available job content.

    HARD RULE:

        If ANY mandatory experience requirement is above
        MAX_JOB_EXPERIENCE_YEARS, the entire job is rejected.

    Preferred requirements are recorded separately.
    """

    title = clean_text(
        job.get("title")
    )

    # --------------------------------------------------------
    # TITLE
    # --------------------------------------------------------

    if title_experience_above_limit(
        title
    ):

        return {
            "found": True,
            "valid": False,
            "hard_rejection": True,
            "maximum_required": float("inf"),
            "mandatory_requirements": [
                {
                    "field": "title",
                    "minimum": None,
                    "maximum": None,
                    "text": title,
                    "reason": (
                        "Title contains "
                        "experience above limit"
                    ),
                }
            ],
            "preferred_requirements": [],
        }

    # --------------------------------------------------------
    # COLLECT FULL CONTENT
    # --------------------------------------------------------

    content_items = (
        extract_experience_content(
            job
        )
    )

    requirements = []

    seen = set()

    # --------------------------------------------------------
    # ANALYSE EVERY CONTENT FIELD
    # --------------------------------------------------------

    for field_name, text in content_items:

        detected = (
            extract_experience_requirements(
                text
            )
        )

        for (
            minimum,
            maximum,
            matched,
            requirement_type,
        ) in detected:

            key = (
                field_name,
                minimum,
                maximum,
                matched,
                requirement_type,
            )

            if key in seen:
                continue

            seen.add(
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
                    "type": requirement_type,
                }
            )

    mandatory = [
        item
        for item in requirements
        if item["type"] != "preferred"
    ]

    preferred = [
        item
        for item in requirements
        if item["type"] == "preferred"
    ]

    # --------------------------------------------------------
    # FIND MAX MANDATORY REQUIREMENT
    # --------------------------------------------------------

    maximum_required = None

    for requirement in mandatory:

        maximum = requirement[
            "maximum"
        ]

        if maximum is None:

            value = float(
                "inf"
            )

        else:

            value = float(
                maximum
            )

        if (
            maximum_required is None
            or value > maximum_required
        ):

            maximum_required = value

    # --------------------------------------------------------
    # HARD REJECTION
    # --------------------------------------------------------

    hard_rejection = False

    if (
        maximum_required is not None
        and maximum_required
        > MAX_JOB_EXPERIENCE_YEARS
    ):

        hard_rejection = True

    return {
        "found": bool(
            requirements
        ),
        "valid": not hard_rejection,
        "hard_rejection": hard_rejection,
        "maximum_required": maximum_required,
        "mandatory_requirements": mandatory,
        "preferred_requirements": preferred,
        "all_requirements": requirements,
    }


# ============================================================
# LOCATION
# ============================================================

def matches_location(job):
    """
    Match preferred locations.

    Do not use TN / KA / TS abbreviations because they can
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


# ============================================================
# ROLE MATCHING
# ============================================================

def role_matches(job):
    """Match genuine target-role titles."""

    title = clean_text(
        job.get("title")
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
        get_job_content_text(
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
            job_content,
            skill,
        )
    ]

    experience = analyse_experience(
        job
    )

    filter_reasons = []

    # --------------------------------------------------------
    # TITLE SENIORITY
    # --------------------------------------------------------

    if has_advanced_title(
        title
    ):

        filter_reasons.append(
            "Advanced/senior-level designation"
        )

    # --------------------------------------------------------
    # SENIORITY METADATA
    # --------------------------------------------------------

    if has_advanced_seniority(
        job
    ):

        filter_reasons.append(
            "Advanced/senior-level metadata"
        )

    # --------------------------------------------------------
    # ADVANCED DOMAIN
    # --------------------------------------------------------

    if has_advanced_domain(
        title
    ):

        filter_reasons.append(
            "Advanced DevOps/SRE designation"
        )

    # --------------------------------------------------------
    # EXPERIENCE HARD GATE
    # --------------------------------------------------------

    if experience[
        "hard_rejection"
    ]:

        maximum = experience[
            "maximum_required"
        ]

        if maximum is None:

            display = (
                "unknown"
            )

        elif maximum == float("inf"):

            display = (
                "open-ended / plus-years"
            )

        else:

            display = (
                f"{maximum:g} years"
            )

        filter_reasons.append(
            "Mandatory experience exceeds "
            f"{MAX_JOB_EXPERIENCE_YEARS:g} years "
            f"(detected: {display})"
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
    # EMPLOYMENT
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
    # SCORE
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

    result = dict(
        job
    )

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

    # --------------------------------------------------------
    # AUDIT DETAILS
    # --------------------------------------------------------

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
    """Normalize company names."""

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
    """Normalize titles."""

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
    """Same company + same designation = duplicate."""

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

def keep_relevant_jobs(
    ranked_jobs
):
    """
    Keep only jobs that pass all hard filters.

    Remove duplicate company/title combinations.
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

def get_rejected_jobs(
    ranked_jobs
):
    """Return all rejected jobs for audit reporting."""

    return [
        job
        for job in ranked_jobs
        if job.get(
            "match_category"
        ) == "Ignore"
    ]
