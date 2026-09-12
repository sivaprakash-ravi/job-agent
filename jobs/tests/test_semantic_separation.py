"""Semantic separation tests (V1.1 Phase 10).

The lexical scorer must separate a genuine target role from a skill
look-alike: a full-stack or product role sharing aws/python/git
tokens must NOT reach the same score as a real DevOps/Support role.
"""

from semantic_job import semantic_score


def devops_job():
    return {
        "title": "DevOps Engineer",
        "description": (
            "AWS, GCP, Azure, Kubernetes, Docker, Terraform, Linux, "
            "CI/CD, monitoring, SRE, reliability, production support, "
            "Python, Java, incident management and troubleshooting."
        ),
    }


def cloud_support_job():
    return {
        "title": "Cloud Support Engineer",
        "description": (
            "AWS, Kubernetes, Linux, troubleshooting, monitoring, "
            "incident response, infrastructure, python scripts, "
            "CI/CD pipelines and cloud operations."
        ),
    }


def full_stack_job():
    return {
        "title": "Full Stack Developer",
        "description": (
            "AWS, Python, Java, SQL, Git, CI/CD, Docker, Kubernetes, "
            "React, Node.js, REST APIs and a modern front-end stack."
        ),
    }


def brand_job():
    return {
        "title": "Brand Manager",
        "description": (
            "We need a marketing leader to grow our consumer brand "
            "through social media campaigns and influencer partnerships."
        ),
    }


def test_devops_beats_full_stack_and_brand():
    devops, _ = semantic_score(devops_job())
    full_stack, _ = semantic_score(full_stack_job())
    brand, _ = semantic_score(brand_job())

    assert devops > full_stack
    assert full_stack >= brand


def test_cloud_support_beats_full_stack():
    support, _ = semantic_score(cloud_support_job())
    full_stack, _ = semantic_score(full_stack_job())

    assert support > full_stack


def test_roles_stay_in_bounds():
    for job in (
        devops_job(),
        full_stack_job(),
        brand_job(),
    ):
        score, _ = semantic_score(job)
        assert 0.0 <= score <= 1.0


def test_role_phrase_count_reported():
    _score, notes = semantic_score(devops_job())

    assert isinstance(notes.get("role_phrases"), int)
    assert notes["role_phrases"] >= 1
    assert notes["backend"] == "lexical"