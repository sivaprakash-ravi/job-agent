"""Country-restricted remote handling (V1.1 Phase 8).

"Remote" by itself, "Remote India" and "Anywhere" match the profile.
Restricted remote such as "Remote - US only", "100% Remote - USA
Only" (sometimes only in the title) or "Remote (Europe)" must NOT
leak into the eligible set as a generic remote job.
"""

from job_matcher import matches_location, score_job


def job(location, title="Cloud Support Engineer", work_mode=""):
    return {
        "title": title,
        "location": location,
        "work_mode": work_mode,
        "description": "Support AWS and Linux systems. 2 years preferred.",
        "skills": ["AWS", "Linux", "GCP", "Docker"],
    }


def test_generic_remote_still_matches():
    for location in ["Remote", "Work from home", "Anywhere"]:
        assert matches_location(job(location)), location


def test_remote_india_matches():
    for location in [
        "Remote India",
        "Remote - India",
        "Remote (India)",
        "Remote, India",
    ]:
        assert matches_location(job(location)), location


def test_remote_apac_not_restricted():
    assert matches_location(job("Remote (APAC)"))


def test_us_only_remote_rejected():
    for location in [
        "Remote - US only",
        "Remote (United States)",
        "Remote, USA",
        "Remote within the US only",
        "Remote - USA",
    ]:
        assert matches_location(job(location)) is False, location


def test_other_region_remote_rejected():
    for location in [
        "Remote - Europe",
        "Remote (EU)",
        "Remote - Canada",
        "Remote - UK only",
        "Remote (EMEA)",
        "Remote - Poland",
    ]:
        assert matches_location(job(location)) is False, location


def test_us_only_in_title_rejected():
    # The restriction sometimes appears only in the title while the
    # location field says a plain "Remote" (observed on a real job).
    target = job(
        "Remote",
        title=(
            "Senior Python/DevOps Engineer "
            "(100% Remote - USA Only)"
        ),
    )

    assert matches_location(target) is False


def test_us_only_in_title_rejects_score():
    target = job(
        "Remote",
        title=(
            "Senior Python/DevOps Engineer "
            "(100% Remote - USA Only)"
        ),
        work_mode="Remote",
    )

    result = score_job(target)

    assert result["match_category"] == "Ignore"
    assert "Outside preferred locations" in (
        result["match_details"]["filter_reasons"]
    )


def test_remote_hybrid_bengaluru_matches():
    assert matches_location(
        job("Bengaluru, Karnataka, India")
    )

    assert matches_location(
        job("Bengaluru, Karnataka, India; Remote")
    )