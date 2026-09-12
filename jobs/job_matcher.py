"""Deep rule-based job matching for the daily job agent."""

import re

from profile import (
    EMPLOYMENT_TYPE,
    ENRICHMENT_PRIORITY_BOOST,
    JOB_FAMILY_LABELS,
    JOB_FAMILY_PRIORITY,
    JOB_FAMILY_RULES,
    LOCATIONS,
    MAX_JOB_EXPERIENCE_YEARS,
    PRIORITY_TIERS,
    RANK_PRIORITY_BOOST,
    SKILLS,
    TARGET_ROLES,
)

from semantic_job import score_job_semantic


MINIMUM_SCORE = 45

QUALIFIED = "qualified"
POSSIBLE_MATCH = "possible_match"
REJECTED = "rejected"


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
# COUNTRY-RESTRICTED REMOTE
# ============================================================
#
# "Remote" on its own, "Remote India" or "Anywhere" match the
# profile. But "Remote - US only", "Remote (Europe)" or
# "100% Remote - USA Only" (sometimes only in the title) do NOT
# match: they restrict hiring to a country/region the profile does
# not target. A job is only restricted when a non-target region is
# named AND no accepted scope (India / global / APAC) is named.

REMOTE_CONFIRM_PHRASES = [
    "india",
    "anywhere",
    "global",
    "worldwide",
    "work from anywhere",
    "all time zones",
    "apac",
    "asia",
]

REMOTE_RESTRICTION_PATTERNS = [
    re.compile(r"\b(?:us|usa|u\.?s\.?|united states)\b", re.IGNORECASE),
    re.compile(r"\bcanada\b", re.IGNORECASE),
    re.compile(r"\b(?:uk|u\.?k\.?|united kingdom)\b", re.IGNORECASE),
    re.compile(r"\b(?:europe|eu|emea)\b", re.IGNORECASE),
    re.compile(
        r"\b(?:germany|france|spain|italy|poland|netherlands|"
        r"brazil|mexico)\b",
        re.IGNORECASE,
    ),
]


def _remote_is_restricted(text):
    """Whether remote text is limited to a non-target country/region."""
    text = clean_text(text)

    if not text:
        return False

    if any(
        contains_phrase(text, phrase)
        for phrase in REMOTE_CONFIRM_PHRASES
    ):
        return False

    return any(
        pattern.search(text)
        for pattern in REMOTE_RESTRICTION_PATTERNS
    )


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
# EXPERIENCE REGEX
# ============================================================

EXPERIENCE_RANGE_PATTERN = re.compile(
    r"\b(\d+(?:\.\d+)?)"
    r"\s*(?:-|to|–|—)"
    r"\s*(\d+(?:\.\d+)?)"
    r"\s*(?:years?|yrs?)\b",
    re.IGNORECASE,
)


EXPERIENCE_PLUS_PATTERN = re.compile(
    r"\b(\d+(?:\.\d+)?)"
    r"\s*(?:\+|plus)"
    r"\s*(?:years?|yrs?)\b"
    r"|"
    r"\b(\d+(?:\.\d+)?)"
    r"\s*(?:years?|yrs?)"
    r"\s*(?:or\s+more|and\s+above|and\s+over)\b",
    re.IGNORECASE,
)


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


AT_LEAST_EXPERIENCE_PATTERN = re.compile(
    r"\bat\s+least\s+"
    r"(\d+(?:\.\d+)?)"
    r"\s*(?:years?|yrs?)\b",
    re.IGNORECASE,
)


APPROXIMATE_EXPERIENCE_PATTERN = re.compile(
    r"\b(?:"
    r"around"
    r"|approximately"
    r"|approx\.?"
    r"|about"
    r"|min\.?"
    r"|minimum"
    r"|at\s+least"
    r"|over"
    r"|more\s+than"
    r"|greater\s+than"
    r"|up\s+to"
    r")\s+"
    r"(\d+(?:\.\d+)?)"
    r"\s*(?:years?|yrs?)\b",
    re.IGNORECASE,
)


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


DIRECT_EXPERIENCE_PATTERN = re.compile(
    r"\b(\d+(?:\.\d+)?)"
    r"\s*(?:years?|yrs?)"
    r"\s*(?:of\s+)?"
    r"(?:"
    r"[a-z][a-z0-9/&,\-]*"
    r"\s+"
    r"){0,8}"
    r"experience\b",
    re.IGNORECASE,
)


REVERSE_EXPERIENCE_PATTERN = re.compile(
    r"\bexperience"
    r"\s*(?:of|:)?\s*"
    r"(\d+(?:\.\d+)?)"
    r"\s*(?:years?|yrs?)\b",
    re.IGNORECASE,
)


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


TITLE_EXPERIENCE_PATTERN = re.compile(
    r"\b(\d+(?:\.\d+)?)"
    r"\s*(?:\+|plus)?"
    r"\s*(?:years?|yrs?)\b",
    re.IGNORECASE,
)


# ============================================================
# GRADUATE / FRESHER FILTER
# ============================================================

GRADUATE_RESTRICTION_PATTERNS = [
    r"\bfreshers?\s+only\b",
    r"\bfresher\s+only\b",
    r"\bfresh\s+graduates?\s+only\b",
    r"\brecent\s+graduates?\s+only\b",
    r"\bgraduates?\s+only\b",
    r"\bcampus\s+hire\b",
    r"\bcampus\s+recruitment\b",
    r"\bcampus\s+recruits?\b",
    r"\bentry[\s-]*level\s+graduates?\s+only\b",
    r"\b2025\s*/\s*2026\s+graduates?\b",
    r"\b2025\s+or\s+2026\s+graduates?\b",
    r"\b2025\s+and\s+2026\s+graduates?\b",
    r"\b2025[\s,/-]+2026\s+graduates?\b",
    r"\b2025\s+graduates?\s+only\b",
    r"\b2026\s+graduates?\s+only\b",
    r"\bgraduating\s+in\s+2025\b",
    r"\bgraduating\s+in\s+2026\b",
    r"\bgraduating\s+class\s+of\s+2025\b",
    r"\bgraduating\s+class\s+of\s+2026\b",
]


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

    Metadata such as dates, IDs, URLs, salary, company
    statistics and source metadata is excluded.
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
# RECURSIVE CONTENT EXTRACTION
# ============================================================

def extract_experience_content(
    value,
    field_name="",
):
    """
    Collect text only from legitimate job-content fields.
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

        if _is_numeric_experience(field_name):

            texts.append(
                (
                    field_name,
                    f"{text} years of "
                    f"experience required",
                )
            )

    return texts


def _is_numeric_experience(field_name):
    """Whether a field is an explicit minimum-experience value."""
    name = (
        str(field_name)
        .lower()
        .replace("_", " ")
        .strip()
    )

    return any(
        marker in name
        for marker in (
            "experience years min",
            "minimum experience",
            "minimum years",
            "required experience",
            "required years",
            "years of experience min",
            "minimum required experience",
        )
    ) and (
        "max" not in name
        and "maximum" not in name
    )


# ============================================================
# GRADUATE ANALYSIS
# ============================================================

def analyse_graduate_restriction(job):
    """
    Detect explicit fresher/graduate/campus restrictions.

    Important:
    A normal mention such as "work with recent graduates"
    does NOT reject the job.

    We only reject explicit candidate restrictions.
    """

    content_items = (
        extract_experience_content(
            job
        )
    )

    findings = []

    for field_name, text in content_items:

        for pattern in GRADUATE_RESTRICTION_PATTERNS:

            for match in re.finditer(
                pattern,
                text,
                re.IGNORECASE,
            ):

                findings.append(
                    {
                        "field": field_name,
                        "text": clean_text(
                            match.group(0)
                        ),
                    }
                )

    unique = []

    seen = set()

    for item in findings:

        key = (
            item["field"],
            item["text"],
        )

        if key in seen:
            continue

        seen.add(
            key
        )

        unique.append(
            item
        )

    return {
        "restricted": bool(
            unique
        ),
        "requirements": unique,
    }


# ============================================================
# SENIORITY
# ============================================================

def has_advanced_seniority(job):
    """Check explicit seniority metadata."""

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


def get_seniority_reasons(job):
    """Return exact seniority metadata evidence."""

    findings = []

    for key, value in job.items():

        key_name = str(
            key
        ).lower().strip()

        if key_name not in SENIORITY_FIELDS:
            continue

        text = clean_text(
            value
        )

        for pattern in ADVANCED_SENIORITY_PATTERNS:

            match = re.search(
                pattern,
                text,
            )

            if match:

                findings.append(
                    {
                        "field": key_name,
                        "text": match.group(0),
                        "value": text,
                    }
                )

                break

    return findings


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
    """
    Reject title experience above the configured limit.

    A plus form such as "2+ years" means "at least 2 years" and is
    acceptable. Only values actually above the limit reject.

    Example:
        3 years  -> reject
        3+ years -> reject
        2+ years -> allowed
        2 years  -> allowed
    """

    title = clean_text(
        title
    )

    for match in TITLE_EXPERIENCE_PATTERN.finditer(
        title
    ):

        years = float(
            match.group(1)
        )

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
    """
    Detect many real-world experience expressions.

    Returns:
        minimum,
        maximum,
        matched_text,
        requirement_type

    requirement_type:
        mandatory
        preferred
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
        kind="single",
    ):

        results.append(
            (
                minimum,
                maximum,
                clean_text(
                    matched
                ),
                requirement_type,
                kind,
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
            kind="range",
        )

    # --------------------------------------------------------
    # PLUS
    #
    # "2+ years" is a minimum-only requirement. It is NOT rejected
    # just because the word "plus" appears. Only values above the
    # configured maximum reject ("3+ years" with max 2).
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
            years,
            match.group(0),
            kind="plus",
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
            kind="plus",
        )

    # --------------------------------------------------------
    # AROUND / APPROXIMATELY / MIN / MORE THAN
    # --------------------------------------------------------

    for match in APPROXIMATE_EXPERIENCE_PATTERN.finditer(
        text
    ):

        years = float(
            match.group(1)
        )

        add(
            years,
            years,
            match.group(0),
            kind="plus",
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
    # IMPORTANT:
    # "plus" is NOT a preferred marker.
    #
    # 3+ years means a real experience requirement.
    # --------------------------------------------------------

    preferred_markers = [
        "preferred",
        "preferably",
        "nice to have",
        "nice-to-have",
        "desired",
        "bonus",
        "good to have",
    ]

    classified = []

    for (
        minimum,
        maximum,
        matched,
        requirement_type,
        kind,
    ) in results:

        context = containing_sentence(
            text,
            matched,
        )

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
                kind,
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
            item[4],
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


def containing_sentence(text, matched):
    """
    Return the sentence or bullet containing ``matched``.

    Experience classification must use the actual sentence / bullet
    that contains the experience statement. A word such as
    "preferred" elsewhere in a large description must not turn a
    mandatory requirement into a preferred one.
    """
    index = text.find(
        matched
    )

    if index < 0:
        return ""

    start_index = index
    end_index = index + len(matched)

    boundary_pattern = re.compile(
        r"[.!?\n]"
    )

    before = list(
        boundary_pattern.finditer(
            text,
            0,
            start_index,
        )
    )

    after = list(
        boundary_pattern.finditer(
            text,
            end_index,
        )
    )

    segment_start = (
        before[-1].end()
        if before
        else 0
    )

    segment_end = (
        after[0].start()
        if after
        else len(text)
    )

    segment = text[
        segment_start:segment_end
    ].strip()

    if len(segment) > 400:
        segment = text[
            max(0, start_index - 120):
            min(len(text), end_index + 120)
        ]

    return segment


# ============================================================
# DEEP EXPERIENCE ANALYSIS
# ============================================================

def analyse_experience(job):
    """
    Deep experience analysis.

    HARD RULE:

        Any mandatory requirement above the configured
        maximum rejects the entire job.

    Plus / "at least" forms ("2+ years", "at least 2 years") are
    minimum-only requirements and are acceptable whenever the value
    is not above the configured maximum.
    """

    title = clean_text(
        job.get("title")
    )

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
                    "type": "mandatory",
                    "reason": (
                        "Title contains "
                        "experience above limit"
                    ),
                }
            ],
            "preferred_requirements": [],
            "all_requirements": [],
        }

    content_items = (
        extract_experience_content(
            job
        )
    )

    requirements = []

    seen = set()

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
            kind,
        ) in detected:

            key = (
                field_name,
                minimum,
                maximum,
                matched,
                requirement_type,
                kind,
            )

            if key in seen:
                continue

            seen.add(
                key
            )

            plausible = [
                value
                for value in (minimum, maximum)
                if value is not None
                and 0 <= value <= 40
            ]

            if not plausible:
                continue

            open_ended = (
                kind == "plus"
            )

            requirements.append(
                {
                    "field": field_name,
                    "minimum": minimum,
                    "maximum": (
                        None
                        if open_ended
                        else maximum
                    ),
                    "text": matched,
                    "type": requirement_type,
                    "open_ended": open_ended,
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

    maximum_required = None

    for requirement in mandatory:

        if requirement["open_ended"]:

            value = float(
                requirement["minimum"]
            )

        else:

            value = float(
                requirement["maximum"]
                if requirement["maximum"] is not None
                else requirement["minimum"]
            )

        if (
            maximum_required is None
            or value > maximum_required
        ):

            maximum_required = value

    hard_rejection = (
        maximum_required is not None
        and maximum_required
        > MAX_JOB_EXPERIENCE_YEARS
    )

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
    """Match preferred locations."""

    location = clean_text(
        job.get("location")
    )

    work_mode = clean_text(
        job.get("work_mode")
        or job.get(
            "remote_work_model"
        )
    )

    title = clean_text(
        job.get("title")
    )

    if "Remote" in LOCATIONS:

        remote_hit = (
            any(
                contains_phrase(
                    location,
                    alias,
                )
                for alias in LOCATION_ALIASES[
                    "Remote"
                ]
            )
            or any(
                contains_phrase(
                    work_mode,
                    alias,
                )
                for alias in LOCATION_ALIASES[
                    "Remote"
                ]
            )
        )

        if remote_hit and not _remote_is_restricted(
            f"{location} {work_mode} {title}".strip()
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

# ============================================================
# ROLE FAMILIES
# ============================================================
#
# Profile-driven taxonomy. Every family phrase names the exact role
# family that belongs to the profile; categories are used for
# diversity-aware enrichment and reporting. The phrase list is
# deliberately strict: adding a generic phrase such as
# "platform engineer" would admit Data Platform / Sales Platform
# roles, so precision is preferred until the sample data proves
# otherwise.

ROLE_FAMILIES = [
    ("application support", "support"),
    ("production support", "support"),
    ("technical support", "support"),
    ("cloud support", "support"),
    ("cloud infrastructure support", "support"),
    ("infrastructure support", "support"),
    ("infrastructure engineer", "infrastructure"),
    ("cloud operations", "infrastructure"),
    ("operations engineer", "infrastructure"),
    ("production operations", "infrastructure"),
    ("application operations", "infrastructure"),
    ("technical operations", "infrastructure"),
    ("qa engineer", "qa"),
    ("quality assurance", "qa"),
    ("software test", "qa"),
    ("test engineer", "qa"),
    ("qa analyst", "qa"),
    ("quality analyst", "qa"),
    ("manual tester", "qa"),
    ("software tester", "qa"),
    ("application tester", "qa"),
    ("devops engineer", "devops"),
    ("junior devops", "devops"),
    ("cloud engineer", "cloud"),
    ("site reliability", "sre"),
    ("sre", "sre"),
]

ROLE_FAMILY_PHRASES = [
    phrase
    for phrase, _category in ROLE_FAMILIES
]


def role_categories(matched_roles):
    """Return the profile role families matched by a job title."""
    categories = set()

    for role in matched_roles:
        role_clean = clean_text(role)

        for phrase, category in ROLE_FAMILIES:
            if contains_phrase(role_clean, phrase):
                categories.add(category)
                break

    return categories


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

    for family in ROLE_FAMILY_PHRASES:

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
# CAREER JOB-FAMILY DETECTION
# ============================================================
#
# Career priority is purely a ranking / enrichment / reporting
# signal. It NEVER widens eligibility: a job still has to pass the
# existing role-family gate, experience gate, location gate etc.
# Family detection inspects the title plus the JD content so generic
# "support" / "quality" roles are not adopted and the highest-priority
# genuinely-applicable family wins.

def _family_content_text(job):
    parts = []

    for key in (
        "title",
        "description",
        "full_job_page_text",
        "job_description",
        "responsibilities",
        "requirements",
        "qualifications",
        "skills",
    ):
        value = job.get(key)
        if value is None:
            continue
        if isinstance(value, (list, tuple)):
            value = " ".join(str(item) for item in value)
        if value:
            parts.append(clean_text(value))

    return " ".join(parts).strip()


def detect_job_family(job):
    """Return the highest-priority genuinely-applicable family.

    Returns ``None`` when no family is genuinely applicable (e.g. a
    call-center customer-service role). Multi-family jobs are resolved
    by (priority, then strong-before-weak title evidence) so a precise
    title match always beats a generic one inside the same tier.
    """
    text = _family_content_text(job)
    title = clean_text(job.get("title") or "")

    candidates = []

    for family, rule in JOB_FAMILY_RULES.items():

        exclude_hit = any(
            contains_phrase(text, phrase)
            for phrase in rule.get("exclude", [])
        )

        if exclude_hit:
            continue

        if any(
            contains_phrase(title, phrase)
            for phrase in rule.get("strong_title", [])
        ):
            candidates.append((family, 0))
            continue

        weak = any(
            contains_phrase(title, phrase)
            for phrase in rule.get("weak_title", [])
        )

        if not weak:
            continue

        evidence_hit = any(
            contains_phrase(text, phrase)
            for phrase in rule.get("evidence", [])
        )

        if evidence_hit:
            candidates.append((family, 1))

    if not candidates:
        return None

    candidates.sort(
        key=lambda family_strength: (
            JOB_FAMILY_PRIORITY.get(
                family_strength[0], 99
            ),
            family_strength[1],
            family_strength[0],
        )
    )

    return candidates[0][0]


def priority_profile(job):
    """Return the career-priority metadata for a job."""
    family = detect_job_family(job)

    if family is None:
        return {
            "job_family": None,
            "career_priority": None,
            "priority_tier": None,
            "priority_label": None,
        }

    priority = JOB_FAMILY_PRIORITY.get(
        family, 3
    )

    tier = PRIORITY_TIERS.get(
        priority, "P3"
    )

    return {
        "job_family": family,
        "career_priority": priority,
        "priority_tier": tier,
        "priority_label": JOB_FAMILY_LABELS.get(
            family, family.replace("_", " ").title()
        ),
    }


def job_priority_tier(job):
    """Priority tier for a job: P1 / P2 / P3 / None."""
    tier = job.get("priority_tier")
    if tier:
        return tier
    profile = priority_profile(job)
    return profile.get("priority_tier")


def rank_priority_boost(job):
    """Ranking-only priority boost (never touches match_score)."""
    tier = job.get("priority_tier")
    if not tier:
        tier = job_priority_tier(job)
    return RANK_PRIORITY_BOOST.get(tier, 0) if tier else 0


def job_rank_key(job):
    """Ordering key that blends relevance and career priority.

    match_score stays the relevance truth (and the qualification
    gate); the small priority boost only reorders jobs that are
    already equally relevant enough to be compared.
    """
    explicit = job.get("rank_score")
    if explicit is not None:
        return float(explicit)

    score = float(
        job.get("match_score") or 0
    )

    return score + rank_priority_boost(job)


# ============================================================
# CHEAP PREFILTER (pre-enrichment signal)
# ============================================================

PREFILTER_EXTRA_TERMS = {
    "support engineer",
    "support",
    "operations",
    "systems",
    "admin",
    "troubleshooting",
    "incident",
    "monitoring",
    "production",
    "reliability",
    "cloud",
    "infrastructure",
    "deployment",
    "ci/cd",
    "observability",
}


def prefilter_job(job):
    """Cheap relevance signal on raw discovery data.

    Used to PRIORITIZE which jobs get full-page enrichment, never as
    a hard gate, so recall is preserved when the raw listing is thin.
    """
    title = clean_text(
        job.get("title")
    )

    content = get_job_content_text(
        job
    ) + " "

    for key in (
        "description",
        "requirements",
        "responsibilities",
        "skills",
    ):
        value = job.get(key)

        if isinstance(value, (list, tuple)):
            value = " ".join(
                str(item)
                for item in value
            )

        content += clean_text(value) + " "

    if role_matches(job):
        return True

    if any(
        contains_phrase(content, skill)
        for skill in SKILLS
    ):
        return True

    return any(
        contains_phrase(content, term)
        for term in PREFILTER_EXTRA_TERMS
    )


def prioritize_for_enrichment(jobs):
    """Split jobs into (likely_relevant, rest) using the cheap signal."""
    relevant = []
    rest = []

    for job in jobs:
        if prefilter_job(job):
            relevant.append(job)
        else:
            rest.append(job)

    return relevant, rest


def enrichment_priority(job):
    """Cheap conservative pre-enrichment priority score (0-100).

    This only ORDERS jobs for the enrichment cap. It never rejects,
    so a thin or incomplete raw listing keeps every chance to be
    enriched, scored and passed on by the full matcher.

    Signals, in order of weight:
        role family in title        (+38)
        profile skills in listing   (+18 max)
        location matches profile    (+12)
        lexical role-phrase signal  (+12 max)
    """
    score = 0.0

    if role_matches(job):
        score += 38

    content = get_job_content_text(job)

    for key in (
        "description",
        "requirements",
        "responsibilities",
        "skills",
    ):
        value = job.get(key)

        if isinstance(value, (list, tuple)):
            value = " ".join(
                str(item)
                for item in value
            )

        content += " " + clean_text(value)

    skill_hits = 0

    for skill in SKILLS:
        if contains_phrase(content, skill):
            skill_hits += 1

        if skill_hits >= 6:
            break

    score += min(18, skill_hits * 3)

    if matches_location(job):
        score += 12

    try:
        lexical, _notes = semantic_score(job)
    except Exception:
        lexical = 0.0

    if lexical > 0:
        score += round(lexical * 12)

    tier = job.get("priority_tier")
    priority = job.get("career_priority")

    if not tier or priority is None:
        profile = priority_profile(job)
        tier = (
            job.get("priority_tier")
            or profile.get("priority_tier")
        )
        priority = (
            job.get("career_priority")
            or profile.get("career_priority")
        )

    if (
        tier
        and priority is not None
        and priority in ENRICHMENT_PRIORITY_BOOST
    ):
        score += ENRICHMENT_PRIORITY_BOOST[priority]

    return min(100, int(round(score)))


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

    graduate = (
        analyse_graduate_restriction(
            job
        )
    )

    filter_reasons = []

    seniority_penalty = 0

    # --------------------------------------------------------
    # TITLE SENIORITY (soft signal)
    #
    # A senior-sounding title alone is NOT a hard rejection.
    # The actual experience requirements in the job decide.
    # --------------------------------------------------------

    if has_advanced_title(
        title
    ):

        seniority_penalty += 20

    # --------------------------------------------------------
    # SENIORITY METADATA
    # --------------------------------------------------------

    seniority_reasons = (
        get_seniority_reasons(
            job
        )
    )

    if seniority_reasons:

        for item in seniority_reasons:

            seniority_penalty += 15

    # --------------------------------------------------------
    # ADVANCED DOMAIN TITLE
    # --------------------------------------------------------

    if has_advanced_domain(
        title
    ):

        seniority_penalty += 15

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

            display = "unknown"

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
    # GRADUATE / FRESHER HARD GATE
    # --------------------------------------------------------

    if graduate[
        "restricted"
    ]:

        evidence = "; ".join(
            item["text"]
            for item in graduate[
                "requirements"
            ]
        )

        filter_reasons.append(
            "Graduate/fresher restriction: "
            + evidence
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
    #
    # A job is relevant when its title belongs to a target role
    # family (TARGET_ROLES or a configured family phrase). A strong
    # family title stays relevant even when the fetched JD is empty,
    # so generic skill overlap is deliberately not a substitute.
    #
    # Roles that do NOT belong to a target family must NOT pass just
    # because the description happens to contain generic skills.
    # --------------------------------------------------------

    if not matched_roles:

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
            + experience_score
            - seniority_penalty,
        ),
    )

    # --------------------------------------------------------
    # LIGHTWEIGHT SEMANTIC LAYER (additive, bonus off by default)
    # --------------------------------------------------------

    semantic_extra, semantic_bonus = score_job_semantic(job)

    score = max(
        0,
        min(
            100,
            score + semantic_bonus,
        ),
    )

    passes = not filter_reasons

    if not passes:
        qualification = REJECTED
    elif score >= MINIMUM_SCORE:
        qualification = QUALIFIED
    else:
        qualification = POSSIBLE_MATCH

    result = dict(
        job
    )

    result[
        "match_score"
    ] = score

    result[
        "qualification"
    ] = qualification

    # --------------------------------------------------------
    # CAREER PRIORITY (ranking / enrichment / reporting only)
    # --------------------------------------------------------

    profile_meta = priority_profile(
        job
    )

    result.update(
        profile_meta
    )

    result[
        "priority_boost"
    ] = rank_priority_boost(
        result
    )

    result[
        "rank_score"
    ] = (
        score + result["priority_boost"]
    )

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
    # COMPLETE AUDIT DETAILS
    # --------------------------------------------------------

    reasons = list(filter_reasons)

    if passes:
        reasons = []

        if matched_roles:
            reasons.append(
                "Role matches: "
                + ", ".join(matched_roles)
            )

        if matched_skills:
            reasons.append(
                "Skills matched: "
                f"{len(matched_skills)}"
            )

        if matches_location(job):
            reasons.append(
                "Location within profile"
            )

        if (
            experience.get("valid")
            and experience.get("found")
        ):
            reasons.append(
                "Experience requirement valid"
            )

    result[
        "match_details"
    ] = {
        "matched_roles": matched_roles,
        "matched_skills": matched_skills,
        "experience_analysis": experience,
        "graduate_analysis": graduate,
        "seniority_analysis": seniority_reasons,
        "seniority_penalty": seniority_penalty,
        "filter_reasons": filter_reasons,
        "reasons": reasons,
        "score_breakdown": {
            "role_score": role_score,
            "skill_score": skill_score,
            "location_score": location_score,
            "experience_score": experience_score,
            "seniority_penalty": seniority_penalty,
            "semantic_bonus": semantic_bonus,
            "total": score,
        },
    }

    result["match_details"].update(semantic_extra)

    return result


# ============================================================
# NEAR-MISS SCORE (for possible-false-negative reporting)
# ============================================================

def near_miss_score_from_details(match_details):
    """Closeness of a rejected job BEFORE every hard gate.

    Sums the role/skills/location components and applies only the
    seniority soft-penalty, deliberately ignoring the experience
    hard gate. A high score means "this job would have been
    eligible if one hard gate had not fired."
    """
    breakdown = (
        (match_details or {})
        .get("score_breakdown") or {}
    )

    near = (
        breakdown.get("role_score", 0)
        + breakdown.get("skill_score", 0)
        + breakdown.get("location_score", 0)
        - 0.5
        * breakdown.get(
            "seniority_penalty",
            0,
        )
        + 10
    )

    return max(
        0,
        min(
            100,
            round(near),
        ),
    )


# ============================================================
# RANKING
# ============================================================

def rank_jobs(jobs):
    """Rank all collected jobs.

    Ordering blends relevance (match_score) with the small
    career-priority boost; match_score itself is untouched so the
    MINIMUM_SCORE=45 qualification gate keeps its exact behavior.
    """

    ranked = [
        score_job(job)
        for job in jobs
    ]

    return sorted(
        ranked,
        key=job_rank_key,
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

def job_qualification(job):
    """Return the explicit qualification state for a ranked job.

    ``qualified``     - no hard filter reason AND score >= MINIMUM_SCORE
    ``possible_match``- no hard filter reason BUT score < MINIMUM_SCORE
    ``rejected``      - hard filter reason (hard rejection always wins)

    Falls back to deriving the state from the stored match details for
    jobs scored before the field existed (or synthetic test records).
    """
    details = job.get("match_details") or {}

    if not isinstance(details, dict):
        details = {}

    filter_reasons = details.get(
        "filter_reasons"
    ) or []

    if filter_reasons:
        return REJECTED

    stored = job.get("qualification")

    if stored in {
        QUALIFIED,
        POSSIBLE_MATCH,
    }:
        return stored

    score = job.get(
        "match_score",
        0,
    )

    if score >= MINIMUM_SCORE:
        return QUALIFIED

    return POSSIBLE_MATCH


def keep_relevant_jobs(
    ranked_jobs
):
    """Keep jobs qualified on every axis (hard filters + score gate)."""

    relevant = [
        job
        for job in ranked_jobs
        if job_qualification(job) == QUALIFIED
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


def keep_possible_matches(
    ranked_jobs
):
    """Keep no-hard-rejection jobs that fall below the score gate.

    Possible matches are NOT sent to Telegram, but stay available for
    reporting/analysis.
    """

    possible = [
        job
        for job in ranked_jobs
        if job_qualification(job) == POSSIBLE_MATCH
    ]

    unique = []

    seen = set()

    for job in possible:

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
    """Return all hard-filter-rejected jobs for audit reporting."""

    return [
        job
        for job in ranked_jobs
        if job_qualification(job) == REJECTED
    ]
