"""Content-hash deduplication and prefilter tests."""

from canonical import content_dedupe_key, deduplicate_jobs
from job_matcher import prefilter_job, prioritize_for_enrichment


def rich_job(source, url, company, description):
    return {
        "source": source,
        "source_job_id": f"{source}-{url.rstrip('/').split('/')[-1]}",
        "title": "Cloud Support Engineer",
        "company": company,
        "location": "Remote",
        "url": url,
        "description": description,
    }


SHARED_DESC = (
    "We are looking for a Cloud Support Engineer to help customers "
    "with AWS, GCP and Azure infrastructure. You will be responsible "
    "for troubleshooting production incidents, monitoring resources, "
    "automating deployments with Terraform and Kubernetes, coordinating "
    "with engineering teams and maintaining 24x7 operational excellence. "
    "This is a fully remote position with flexible working hours and "
    "generous learning budget for cloud certifications."
)


def test_content_dedupe_key_requires_rich_description():
    thin = rich_job(
        "a",
        "https://a.example/jobs/1",
        "Acme",
        "Short description",
    )

    assert content_dedupe_key(thin) is None

    full = rich_job(
        "a",
        "https://a.example/jobs/2",
        "Acme",
        SHARED_DESC,
    )

    assert content_dedupe_key(full)


def test_content_dedupe_collapses_cross_provider_duplicates():
    left = rich_job(
        "himalayas",
        "https://himalayas.app/jobs/x1",
        "Acme",
        SHARED_DESC,
    )

    right = rich_job(
        "workable",
        "https://jobs.workable.com/view/x2",
        "Acme Inc",
        SHARED_DESC,
    )

    unique = deduplicate_jobs([left, right])

    assert len(unique) == 1
    assert unique[0]["source"] == "himalayas"
    assert "workable" in unique[0]["duplicate_sources"]


def test_content_dedupe_keeps_distinct_jobs():
    left = rich_job(
        "himalayas",
        "https://himalayas.app/jobs/y1",
        "Acme",
        SHARED_DESC,
    )

    right = rich_job(
        "remoteok",
        "https://remoteok.com/jobs/y2",
        "Acme",
        "A completely different QA testing role description with no "
        "shared substance whatsoever across sentence structure, so "
        "the content hashes must differ and both jobs must survive "
        "global deduplication without being merged together wrongly.",
    )

    unique = deduplicate_jobs([left, right])

    assert len(unique) == 2


def test_prefilter_prioritizes_relevant():
    good = {
        "source": "workable",
        "title": "Cloud Support Engineer",
        "description": "AWS, GCP, Kubernetes, troubleshooting",
    }
    poor = {
        "source": "remoteok",
        "title": "Frontend Intern",
        "description": "React and CSS pixel pushing only",
    }

    assert prefilter_job(good) is True
    assert prefilter_job(poor) is False

    relevant, rest = prioritize_for_enrichment([poor, good])

    assert relevant == [good]
    assert rest == [poor]