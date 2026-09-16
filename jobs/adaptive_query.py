"""Adaptive multi-round query orchestration (V1.2).

Round 1 always runs the full balanced profile query set through every
provider. After the round we count unique jobs per priority tier; any
tier below the configurable threshold gets an extra deterministic
round-2 query vocabulary taken from profile.py - never from an LLM -
and those extra queries are run through the qualified providers only.

Every query slot carries attribution
(``query`` -> ``query_family`` / ``priority`` / ``discovery_round``) so
reporting can say exactly which round produced which jobs. The funnels
and the Telegram gate remain unchanged: adaptive rounds only widen
DISCOVERY, never loosen matching.
"""

from collections import Counter

import ai_config
from sources.base import query_family_for


def tier_for_family(family):
    """Priority tier (1/2/3) behind a career family, or None."""
    if not family:
        return None

    from profile import JOB_FAMILY_PRIORITY

    return JOB_FAMILY_PRIORITY.get(family)


def attribution_slots(search_queries, discovery_round=1):
    """Map each round-1 search query to its attribution metadata."""
    slots = {}

    for query in search_queries:
        key = str(query or "").strip().lower()

        if not key:
            continue

        family = query_family_for(query)

        slots[key] = {
            "query_family": family,
            "priority": tier_for_family(family),
            "discovery_round": discovery_round,
        }

    return slots


def build_round2_slots(round2_queries, discovery_round=2):
    """Map each generated round-2 query to its attributed family."""
    slots = {}

    for query, family in round2_queries:
        key = str(query or "").strip().lower()

        if not key:
            continue

        slots[key] = {
            "query_family": family,
            "priority": tier_for_family(family),
            "discovery_round": discovery_round,
        }

    return slots


def discovered_by_priority(unique_jobs):
    """Count unique finish-line jobs per priority tier (P1/P2/P3/None)."""
    from job_matcher import job_priority_tier

    return Counter(
        job_priority_tier(job) or "None"
        for job in unique_jobs
    )


def underrepresented_tiers(by_priority, total, threshold=None):
    """Return priority tiers (int) that are underrepresented.

    A tier is underrepresented when its share of ``total`` unique jobs
    is below ``threshold``. P3 is preserved by construction (it owns
    the broadest round-1 vocabulary) so this only ever returns 1 and/or
    2; an empty result means the discovery balance is fine.
    """
    if threshold is None:
        threshold = ai_config.UNDERREPRESENTATION_THRESHOLD

    if total <= 0:
        return [1, 2]

    tiers = []

    for tier in (1, 2):
        label = "P1" if tier == 1 else "P2"
        share = by_priority.get(label, 0) / total

        if share < threshold:
            tiers.append(tier)

    return tiers


def _available_round2_vocabulary():
    """Return round-2 phrases with their family, in profile order."""
    from profile import (
        ROUND2_FAMILY_PRIORITY,
        ROUND2_P1_ROLES,
        ROUND2_P1_SKILL_PAIRS,
        ROUND2_P2_ROLES,
        ROUND2_ROLE_FAMILIES,
        ROUND2_SKILL_PAIR_FAMILIES,
    )

    phrases = []

    for tier in (1, 2):
        if tier == 1:
            for role in ROUND2_P1_ROLES:
                phrases.append(
                    (role, ROUND2_ROLE_FAMILIES[role])
                )

            for base, skill in ROUND2_P1_SKILL_PAIRS:
                phrases.append(
                    (
                        f"{base} {skill}",
                        ROUND2_SKILL_PAIR_FAMILIES[(base, skill)],
                    )
                )
        else:
            for role in ROUND2_P2_ROLES:
                phrases.append(
                    (role, ROUND2_ROLE_FAMILIES[role])
                )

    # Deterministic order: P1 first, then P2, preserving profile order.
    phrases.sort(
        key=lambda item: (
            ROUND2_FAMILY_PRIORITY.get(
                item[1], 9
            ),
        )
    )

    return phrases


def round2_queries(
    existing_queries,
    underrepresented,
    budget=None,
):
    """Deterministic round-2 vocabulary for the given tiers.

    Returns a list of unique ``(query, family)`` tuples not already
    covered by ``existing_queries`` (case-insensitive), capped at
    ``budget`` (default ``MAX_AI_QUERIES``). Never emits a query that
    round 1 already ran.
    """
    if budget is None:
        budget = ai_config.MAX_AI_QUERIES

    existing = {
        str(query or "").strip().lower()
        for query in existing_queries
    }

    wanted = set(underrepresented)

    if not wanted:
        return []

    vocabulary = _available_round2_vocabulary()

    selected = []
    seen_text = set()

    for query, family in vocabulary:
        priority = tier_for_family(family)

        if priority not in wanted:
            continue

        key = str(query).strip().lower()

        if (
            not key
            or key in existing
            or key in seen_text
        ):
            continue

        selected.append((query, family))
        seen_text.add(key)

        if len(selected) >= budget:
            break

    return selected


def analyze_round(unique_jobs):
    """Yield-analysis for one discovery round.

    Returns a dict with total uniques plus a per-priority counter so
    the orchestrator can decide whether another round is warranted.
    """
    by_priority = discovered_by_priority(unique_jobs)
    total = len(unique_jobs)

    return {
        "total": total,
        "by_priority": dict(
            sorted(
                by_priority.items(),
                key=lambda item: {
                    "P1": 0,
                    "P2": 1,
                    "P3": 2,
                    "None": 3,
                }.get(item[0], 9),
            )
        ),
    }


def expand_queries(profile, existing_queries, results):
    """AI query-expansion hook with deterministic fallback.

    ``results`` is the unique-job pool of the round that just ran. When
    an AI expander is actually configured it is consulted first;
    otherwise (V1.2: always) the deterministic profile vocabulary is
    used so every downstream consumer sees identical behaviour whether
    or not any model is installed.
    """
    hook = ai_config.expander_hook()

    if hook is not None:
        extra = hook(profile, existing_queries, results)

        if extra:
            return list(extra)

    analysis = analyze_round(results)
    by_priority = Counter(analysis["by_priority"])

    underrepresented = underrepresented_tiers(
        by_priority,
        analysis["total"],
    )

    return round2_queries(
        existing_queries,
        underrepresented,
    )


def stamp_attribution(unique_jobs, *slot_maps):
    """Attach ``search_attribution`` to every discovered job.

    Attribution is merged from each round's slot map
    (``query -> ({query_family, priority, discovery_round})``). Jobs
    whose query is not attributable keep their gathered fields but get
    an explicit ``unknown`` attribution so reports never guess.
    """
    attribution_by_query = {}

    for slots in slot_maps:
        attribution_by_query.update(slots or {})

    for job in unique_jobs:
        slot = attribution_by_query.get(
            str(
                job.get("search_query") or ""
            ).strip().lower()
        )

        if slot is None:
            slot = {
                "query_family": "unknown",
                "priority": None,
                "discovery_round": None,
            }

        job["search_attribution"] = dict(slot)

    return attribution_by_query