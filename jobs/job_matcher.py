def extract_all_experience_requirements(job):
    """
    Extract experience requirements ONLY from genuine
    job-requirement/content fields.

    Never scan metadata such as:
    - date_posted
    - posted_at
    - company size
    - employee count
    - revenue
    - IDs
    - URLs
    - salary
    - ratings
    - source metadata
    """

    findings = []
    seen = set()

    # ---------------------------------------------------------
    # ONLY THESE FIELDS CAN CONTAIN EXPERIENCE REQUIREMENTS
    # ---------------------------------------------------------

    allowed_fields = {
        "description",
        "full_job_page_text",
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
        "job_description",
    }

    # ---------------------------------------------------------
    # RECURSIVE SCAN
    # ---------------------------------------------------------

    def scan(value, field_name):

        if isinstance(value, dict):

            for key, item in value.items():

                key_name = str(key).lower().strip()

                # Only descend into explicitly allowed
                # content/requirement fields.
                if key_name in allowed_fields:

                    scan(
                        item,
                        key_name,
                    )

                # Nested enrichment structures may contain
                # legitimate job content.
                elif key_name in {
                    "enrichment",
                    "job",
                    "details",
                    "content",
                    "data",
                }:

                    scan(
                        item,
                        key_name,
                    )

            return

        if isinstance(value, list):

            for item in value:

                scan(
                    item,
                    field_name,
                )

            return

        text = normalise(value)

        if not text:
            return

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

    scan(
        job,
        "",
    )

    return findings
