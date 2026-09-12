"""JobSpy adapter for job boards that JobSpy supports.

Covers: indeed, linkedin, glassdoor, google, zip_recruiter, bayt,
naukri.

JobSpy is an optional dependency. When it is not installed the
adapter reports ``unavailable`` so the rest of the pipeline keeps
running.
"""

from profile import LOCATIONS


JOBSPY_SITES = [
    "indeed",
    "linkedin",
    "glassdoor",
    "google",
    "zip_recruiter",
    "bayt",
    "naukri",
]

MAX_QUERIES = 6
RESULTS_PER_QUERY = 25
HOURS_OLD = 72


def json_safe(value):
    """Convert JobSpy/Pandas values into JSON-safe values."""
    if value is None:
        return ""

    try:
        if value != value:
            return ""
    except Exception:
        pass

    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            pass

    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]

    if isinstance(value, dict):
        return {str(key): json_safe(val) for key, val in value.items()}

    return str(value)


def normalize_jobspy_job(job):
    """Normalize one JobSpy row into the common schema."""
    from sources.base import normalize_common

    raw = {}

    for column in job.index:
        key = str(column)

        try:
            value = job[column]
        except Exception:
            value = ""

        raw[key] = json_safe(value)

    source = str(raw.get("site") or raw.get("source") or "jobspy")

    title = str(raw.get("title") or "")
    company = str(raw.get("company") or raw.get("company_name") or "")
    location = str(raw.get("location") or "")
    description = str(raw.get("description") or "")
    url = str(raw.get("job_url") or raw.get("url") or "")
    date_posted = str(raw.get("date_posted") or raw.get("posted_at") or "")
    job_type = str(raw.get("job_type") or raw.get("employment_type") or "")
    source_job_id = str(raw.get("id") or "")

    skills = raw.get("job_skills")
    skills = skills if isinstance(skills, list) else []

    is_remote = raw.get("is_remote", False)
    remote = bool(is_remote)

    job = normalize_common(
        source=source,
        source_job_id=source_job_id,
        title=title,
        company=company,
        location=location,
        remote=remote,
        url=url,
        description=description,
        date_posted=date_posted,
        employment_type=job_type,
        skills=skills,
        raw=raw,
    )

    return job


def run(search_queries, locations=None):
    """Run JobSpy searches and return normalized jobs + status."""
    result = {
        "provider": "jobspy",
        "status": "ok",
        "count": 0,
        "error": "",
        "jobs": [],
    }

    try:
        from jobspy import scrape_jobs
    except ImportError:
        result["status"] = "unavailable"
        result["error"] = (
            "python-jobspy is not installed on this runner"
        )
        return result

    queries = search_queries[:MAX_QUERIES]

    if locations is None:
        locations = [loc for loc in LOCATIONS if loc]

    jobs = []

    for location in locations:
        for query in queries:
            try:
                google_search_term = f"{query} {location}"

                frame = scrape_jobs(
                    site_name=JOBSPY_SITES,
                    search_term=query,
                    google_search_term=google_search_term,
                    location=location,
                    results_wanted=RESULTS_PER_QUERY,
                    hours_old=HOURS_OLD,
                    country_indeed="India",
                    verbose=0,
                )
            except Exception as error:
                result["error"] = str(error)
                continue

            if frame is None:
                continue

            for _, row in frame.iterrows():
                job = normalize_jobspy_job(row)

                if not job["url"]:
                    continue

                job["search_query"] = query
                job["search_location"] = location

                jobs.append(job)

    seen = set()
    unique_jobs = []

    for job in jobs:
        key = (
            job["url"].lower()
            or job["source_job_id"]
        )

        if not key or key in seen:
            continue

        seen.add(key)
        unique_jobs.append(job)

    result["jobs"] = unique_jobs
    result["count"] = len(unique_jobs)

    return result