"""Sent-job history behavior tests."""

import collect_jobs
from canonical import job_identity


def sample_job(identity_seed):
    return {
        "source": "greenhouse",
        "source_job_id": identity_seed,
        "title": "Cloud Engineer",
        "company": "Acme",
        "location": "Chennai",
        "url": f"https://boards.greenhouse.io/acme/jobs/{identity_seed}",
    }


def test_save_and_load_sent_jobs(tmp_path, monkeypatch):
    monkeypatch.setattr(
        collect_jobs,
        "SENT_FILE",
        tmp_path / "sent_jobs.json",
    )

    job = sample_job("1")

    sent = collect_jobs.load_sent_jobs()
    assert not sent

    sent.add(job_identity(job))
    collect_jobs.save_sent_jobs(sent)

    loaded = collect_jobs.load_sent_jobs()

    assert job_identity(job) in loaded


def test_sent_history_filters_new_jobs(tmp_path):
    old_job = sample_job("old")
    new_job = sample_job("new")

    sent = {job_identity(old_job)}

    new_jobs = [
        job
        for job in (old_job, new_job)
        if job_identity(job) not in sent
    ]

    assert new_jobs == [new_job]


def test_identity_based_on_url(tmp_path):
    job = sample_job("abc")

    identity = job_identity(job)

    assert identity.startswith("url:")
    assert identity.endswith("/jobs/abc")


def test_stratified_jobs_spreads_across_sources():
    jobs = []

    for source in ("greenhouse", "himalayas", "remoteok", "freehire"):
        for index in range(12):
            jobs.append(
                {
                    "source": source,
                    "source_job_id": f"{source}-{index}",
                    "title": f"Job {index}",
                }
            )

    selected = collect_jobs._stratified_jobs(jobs, 10)

    assert len(selected) == 10
    assert len({job["source"] for job in selected}) == 4

    counts = {}

    for job in selected:
        counts[job["source"]] = counts.get(job["source"], 0) + 1

    assert max(counts.values()) - min(counts.values()) <= 1


def test_stratified_cap_exceeds_pool_returns_all():
    jobs = [
        {"source": "freehire", "title": "A"},
        {"source": "freehire", "title": "B"},
    ]

    selected = collect_jobs._stratified_jobs(jobs, 100)

    assert len(selected) == 2