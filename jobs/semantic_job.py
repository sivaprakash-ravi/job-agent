"""Lightweight, optional semantic relevance layer.

V1 ships with a fast lexical backend that needs no ML dependencies,
so the pipeline stays safe in GitHub Actions. An optional embedding
backend can be enabled with ``JOB_AGENT_SEMANTIC=embed`` when a
sentence-transformers model is installed.

The layer is purely additive to the rule-based scorer:

- ``semantic_score`` is always recorded next to the rule-based score
- by default it is informational (bonus disabled) so existing
  match thresholds and tests are unchanged
- enabling the bonus simply nudges the final score a little
"""

import os
import re


BONUS_ENABLED = (
    os.environ.get("JOB_AGENT_SEMANTIC_BONUS", "").lower()
    in {"1", "true", "yes", "on"}
)

BACKEND = os.environ.get("JOB_AGENT_SEMANTIC", "lexical").lower()


def _identity_tokens():
    """Concept tokens derived from the profile (single source of truth)."""
    from profile import SKILLS, TARGET_ROLES

    tokens = set()

    for role in TARGET_ROLES:
        for word in re.findall(r"[a-z0-9]+", role.lower()):
            if len(word) > 2:
                tokens.add(word)

    for skill in SKILLS:
        for word in re.findall(r"[a-z0-9]+", skill.lower()):
            if len(word) > 2:
                tokens.add(word)

    tokens |= {
        "devops",
        "sre",
        "reliability",
        "cloud",
        "infrastructure",
        "support",
        "operations",
        "qa",
        "testing",
        "linux",
        "aws",
        "gcp",
        "azure",
        "kubernetes",
        "docker",
        "python",
        "java",
        "troubleshooting",
        "incident",
        "monitoring",
    }

    return tokens


def _job_text(job):
    """Cheap concatenation of the searchable job content."""
    pieces = []

    for key in (
        "title",
        "description",
        "requirements",
        "responsibilities",
        "skills",
        "full_job_page_text",
        "job_description",
    ):
        value = job.get(key)

        if isinstance(value, (list, tuple)):
            value = " ".join(str(item) for item in value)

        if value:
            pieces.append(str(value).lower())

    return " ".join(pieces)


def _lexical_score(text):
    """Token-overlap similarity between the profile and a job."""
    tokens = _identity_tokens()

    job_tokens = set(
        word
        for word in re.findall(
            r"[a-z0-9]+",
            text,
        )
        if len(word) > 2
    )

    if not job_tokens:
        return 0.0

    overlap = len(tokens & job_tokens)

    return min(1.0, overlap / 8.0)


def _embedding_score(text):
    """Optional embedding cosine similarity (guarded import)."""
    try:
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer("all-MiniLM-L6-v2")
        profile_terms = " ".join(sorted(_identity_tokens()))

        embeddings = model.encode(
            [profile_terms, text[:2000]]
        )
        import numpy as np

        a = np.asarray(embeddings[0])
        b = np.asarray(embeddings[1])

        norm = float(
            np.linalg.norm(a) * np.linalg.norm(b)
        )

        if norm == 0:
            return 0.0

        return float(
            np.dot(a, b) / norm
        )
    except Exception:
        return None


def semantic_score(job):
    """Return ``(score 0..1, notes dict)`` for one job."""
    text = _job_text(job)

    if not text.strip():
        return 0.0, {"backend": "lexical", "note": "empty content"}

    score = _lexical_score(text)

    notes = {
        "backend": "lexical",
        "tokens_measured": min(
            8.0,
            len(
                set(
                    re.findall(r"[a-z0-9]+", text)
                )
            ),
        ),
    }

    if BACKEND == "embed":
        embedded = _embedding_score(text)

        if embedded is not None:
            score = embedded
            notes["backend"] = "embed"

    return score, notes


def score_job_semantic(job, match_details=None):
    """Add semantic relevance to a scored job (non-destructive)."""
    score, notes = semantic_score(job)

    extra = {}

    extra["semantic_score"] = round(score, 3)
    extra["semantic_notes"] = notes

    if BONUS_ENABLED:
        bonus = round(score * 5)

        if match_details and isinstance(match_details, dict):
            extra["semantic_bonus"] = bonus

    return extra, (bonus if BONUS_ENABLED else 0)