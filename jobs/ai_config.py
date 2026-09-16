"""Adaptive discovery / optional AI configuration (V1.2).

Every value is env-overridable so the deterministic pipeline keeps
identical behaviour on GitHub Actions and on a local box, with or
without any AI model installed.

Defaults keep the pipeline fully deterministic and free:
- AI_ENABLED is False unless explicitly turned on.
- AI_MODE is "off". "local" / "api" are honoured only when an
  expander/semantic implementation actually exists (they do not for
  V1.2, so the deterministic fallback runs).
- All budgets bound the number of web requests / evaluations so a
  discovery run can never spin out of control.
"""

import os


def _env_bool(name, default=False):
    raw = os.environ.get(name, "").strip().lower()

    if not raw:
        return default

    return raw in {
        "1",
        "true",
        "yes",
        "on",
    }


def _env_int(name, default):
    raw = os.environ.get(name, "").strip()

    if not raw:
        return default

    try:
        return int(raw)
    except ValueError:
        return default


def _env_float(name, default):
    raw = os.environ.get(name, "").strip()

    if not raw:
        return default

    try:
        return float(raw)
    except ValueError:
        return default


# Total discovery rounds (round 1 always runs; 2 and 3 are adaptive).
MAX_SEARCH_ROUNDS = _env_int("MAX_SEARCH_ROUNDS", 3)

# Keep the default small even when AI is enabled, so a query budget can
# never explode into thousands of provider requests.
MAX_AI_QUERIES = _env_int("MAX_AI_QUERIES", 30)

# Cap on web lookups for public-source discovery (career pages / ATS).
MAX_SOURCE_LOOKUPS = _env_int("MAX_SOURCE_LOOKUPS", 20)

# Cap on per-round candidate re-ranking evaluations (unused when AI off).
MAX_AI_EVALUATIONS = _env_int("MAX_AI_EVALUATIONS", 100)

# A tier is "underrepresented" when its share of discovered unique jobs
# falls below this fraction. P1 targets the default; P2 gets the same
# threshold so rounding on small totals cannot silently starve QA.
UNDERREPRESENTATION_THRESHOLD = _env_float(
    "UNDERREPRESENTATION_THRESHOLD",
    0.10,
)

# Global master switch: when False every adaptive branch collapses to
# its deterministic fallback and nothing AI-flavoured ever runs.
AI_ENABLED = _env_bool("AI_ENABLED", False)

# off | local | api
AI_MODE = os.environ.get("AI_MODE", "off").strip().lower()

# Adaptive source discovery is additive metadata only: candidate
# career/ATS domains for a human to review. It is gated by this flag
# (default off) so GitHub Actions never teleports into unknown hosts.
SOURCE_DISCOVERY_ENABLED = _env_bool("JOB_AGENT_SOURCE_DISCOVERY", False)


def adaptive_discovery_enabled():
    """Whether the round-based adaptive discovery loop is active.

    The adaptive loop itself never depends on AI: round 2/3 queries
    come from a deterministic profile vocabulary. It is therefore
    safe (and recommended) to leave it enabled with AI off.
    """
    disable = _env_bool(
        "JOB_AGENT_DISABLE_ADAPTIVE",
        False,
    )

    return not disable


def expander_hook():
    """Return a callable for AI query expansion, or ``None``.

    V1.2 has no external AI integration by design: with AI_ENABLED
    False, or AI_MODE off, or no model runtime available, this returns
    ``None`` and the pipeline uses the deterministic fallback.
    """
    if not AI_ENABLED:
        return None

    if AI_MODE not in {"local", "api"}:
        return None

    # No model runtime is bundled, so local/api modes gracefully
    # degrade to the deterministic fallback instead of failing.
    return None