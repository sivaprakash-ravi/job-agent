"""V1.2 Adaptive multi-source discovery tests.

Everything here targets the deterministic layer:
- AI is off by default and every adaptive branch falls back to the
  deterministic profile vocabulary.
- Budgets (query / source-lookup / rounds) are hard caps.
- Discovered jobs keep query / query_family / priority / round
  attribution, and cross-round dedupe keeps the first discovery.
- Source discovery never auto-activates an arbitrary source.
"""

from collections import Counter

import adaptive_query
import ai_config
import profile
import source_discovery
from canonical import deduplicate_jobs
from sources.base import build_search_queries


def make_job(title, url, query, description="", source="workable"):
    return {
        "source": source,
        "source_job_id": f"job-{url}",
        "title": title,
        "company": "Acme",
        "url": f"https://boards.example.com/{url}",
        "location": "Remote",
        "description": description,
        "search_query": query,
        "search_location": "Remote",
    }


# ============================================================
# AI disabled / deterministic fallback
# ============================================================

def test_ai_off_unavailable_defaults():
    assert ai_config.AI_ENABLED is False
    assert ai_config.AI_MODE in {"off", "local", "api"}
    assert ai_config.expander_hook() is None


def test_expand_queries_uses_deterministic_fallback(monkeypatch):
    monkeypatch.setattr(
        ai_config,
        "expander_hook",
        lambda: None,
    )

    p1_job = make_job(
        "DevOps Engineer",
        "d1",
        "DevOps",
        description="AWS Kubernetes Terraform monitoring on-call",
    )
    p3_heavy = []

    for index in range(40):
        p3_heavy.append(
            make_job(
                "Cloud Engineer",
                f"c{index}",
                "Cloud Engineer",
            )
        )

    extra = adaptive_query.expand_queries(
        profile,
        ["DevOps", "Cloud Engineer"],
        [p1_job] + p3_heavy,
    )

    assert isinstance(extra, list)
    assert extra, "deterministic round-2 vocabulary must be produced"


# ============================================================
# P1 / P2 underrepresentation
# ============================================================

def test_underrepresented_tiers_p1_only():
    by_priority = Counter({"P1": 8, "P2": 60, "P3": 400})

    tiers = adaptive_query.underrepresented_tiers(
        by_priority,
        sum(by_priority.values()),
        threshold=0.10,
    )

    assert tiers == [1]


def test_underrepresented_tiers_p2_only():
    by_priority = Counter({"P1": 50, "P2": 5, "P3": 300})

    tiers = adaptive_query.underrepresented_tiers(
        by_priority,
        sum(by_priority.values()),
        threshold=0.10,
    )

    assert tiers == [2]


def test_underrepresented_tiers_none_when_balanced():
    by_priority = Counter({"P1": 30, "P2": 35, "P3": 200})

    tiers = adaptive_query.underrepresented_tiers(
        by_priority,
        sum(by_priority.values()),
        threshold=0.10,
    )

    assert tiers == []


def test_underrepresented_tiers_empty_total():
    assert adaptive_query.underrepresented_tiers(
        Counter(),
        0,
    ) == [1, 2]


def test_round2_queries_target_p1_roles():
    queries = adaptive_query.round2_queries(
        [],
        [1],
        budget=100,
    )

    roles = [query for query, _family in queries]

    assert "Technical Support Engineer" in roles
    assert "Application Support Engineer" in roles
    assert "Production Support Engineer" in roles
    assert "L2 Support Engineer" in roles


def test_round2_queries_target_p2_roles():
    queries = adaptive_query.round2_queries(
        [],
        [2],
        budget=100,
    )

    roles = [query for query, _family in queries]

    assert "QA Automation Engineer" in roles
    assert "SDET" in roles
    assert "Software Test Engineer" in roles


def test_round2_skill_pairs_survive():
    queries = adaptive_query.round2_queries(
        [],
        [1],
        budget=100,
    )

    phrases = [query for query, _family in queries]

    assert "Application Support Java" in phrases
    assert "Cloud Support AWS" in phrases


def test_round2_never_emits_p3():
    queries = adaptive_query.round2_queries(
        [],
        [1, 2],
        budget=100,
    )

    families = {family for _query, family in queries}

    assert families <= {
        "technical_support",
        "application_support",
        "production_support",
        "operations_support",
        "cloud_support",
        "qa_testing",
    }


# ============================================================
# Budgets / round caps
# ============================================================

def test_max_query_budget_respected():
    queries = adaptive_query.round2_queries(
        [],
        [1],
        budget=5,
    )

    assert len(queries) == 5


def test_round2_skips_existing_queries():
    round1 = build_search_queries()
    queries = adaptive_query.round2_queries(
        round1,
        [1, 2],
        budget=1000,
    )

    lowered = {
        str(query).lower()
        for query in round1
    }

    for query, _family in queries:
        assert query.lower() not in lowered


def test_round2_empty_when_no_tiers():
    assert adaptive_query.round2_queries(
        [],
        [],
    ) == []


def test_expansion_halts_when_vocabulary_exhausted():
    vocabulary = adaptive_query._available_round2_vocabulary()
    existing = [query for query, _family in vocabulary]

    queries = adaptive_query.round2_queries(
        existing,
        [1, 2],
        budget=1000,
    )

    assert queries == []


# ============================================================
# Attribution
# ============================================================

def test_round1_attribution_slots():
    slots = adaptive_query.attribution_slots(
        ["Technical Support"],
        1,
    )

    slot = slots["technical support"]

    assert slot["query_family"] == "technical_support"
    assert slot["priority"] == 1
    assert slot["discovery_round"] == 1


def test_round2_attribution_slots():
    slots = adaptive_query.build_round2_slots(
        [("Technical Support Engineer", "technical_support")],
        2,
    )

    slot = slots["technical support engineer"]

    assert slot["query_family"] == "technical_support"
    assert slot["priority"] == 1
    assert slot["discovery_round"] == 2


def test_stamp_attribution_unknown_fallback():
    jobs = [make_job("DevOps", "x", "NonExistent Query")]

    adaptive_query.stamp_attribution(
        jobs,
        adaptive_query.attribution_slots(
            ["Technical Support"],
            1,
        ),
    )

    assert jobs[0]["search_attribution"]["query_family"] == "unknown"
    assert jobs[0]["search_attribution"]["discovery_round"] is None


def test_stamp_attribution_round2_job():
    jobs = [
        make_job(
            "QA Automation Engineer",
            "q1",
            "QA Automation Engineer",
        )
    ]

    adaptive_query.stamp_attribution(
        jobs,
        adaptive_query.attribution_slots(
            ["DevOps", "Technical Support"],
            1,
        ),
        adaptive_query.build_round2_slots(
            [("QA Automation Engineer", "qa_testing")],
            2,
        ),
    )

    attribution = jobs[0]["search_attribution"]

    assert attribution["query_family"] == "qa_testing"
    assert attribution["priority"] == 2
    assert attribution["discovery_round"] == 2


# ============================================================
# Cross-round dedupe keeps first discovery
# ============================================================

def test_dedupe_across_rounds_keeps_round1_attribution():
    job = make_job(
        "Technical Support Engineer",
        "t1",
        "Technical Support",
        description="support + troubleshooting logs",
    )

    same_job_round2 = make_job(
        "Technical Support Engineer",
        "t1",
        "Technical Support Engineer",
        description="support + troubleshooting logs",
    )

    round1_slots = adaptive_query.attribution_slots(
        ["Technical Support"],
        1,
    )
    round2_slots = adaptive_query.build_round2_slots(
        [("Technical Support Engineer", "technical_support")],
        2,
    )

    merged = deduplicate_jobs(
        [job, same_job_round2]
    )

    assert len(merged) == 1

    adaptive_query.stamp_attribution(
        merged,
        round1_slots,
        round2_slots,
    )

    assert merged[0]["search_attribution"]["discovery_round"] == 1


# ============================================================
# Source discovery: ATS detection / safety
# ============================================================

def test_ats_detection_known_vendors():
    assert source_discovery.detect_ats_type(
        "https://boards.greenhouse.io/acme"
    ) == "greenhouse"
    assert source_discovery.detect_ats_type(
        "https://jobs.lever.co/acme"
    ) == "lever"
    assert source_discovery.detect_ats_type(
        "https://jobs.ashbyhq.com/acme"
    ) == "ashby"
    assert source_discovery.detect_ats_type(
        "https://jobs.workable.com/view/1"
    ) == "workable"
    assert source_discovery.detect_ats_type(
        "https://jobs.smartrecruiters.com/acme"
    ) == "smartrecruiters"
    assert source_discovery.detect_ats_type(
        "https://acme.recruitee.com"
    ) == "recruitee"
    assert source_discovery.detect_ats_type(
        "https://acme.teamtailor.com"
    ) == "teamtailor"
    assert source_discovery.detect_ats_type(
        "https://jobs.personio.de/acme"
    ) == "personio"


def test_unknown_source_not_autoactivated():
    assert (
        source_discovery.detect_ats_type(
            "https://sketchy.example.com/eval.php?cmd=1"
        )
        is None
    )


def test_ddgs_unavailable_returns_unavailable(monkeypatch):
    monkeypatch.setattr(
        source_discovery,
        "_load_ddgs",
        lambda: (None, "not installed"),
    )

    status, candidates, error = (
        source_discovery.discover_sources(
            ["Technical Support Engineer"],
        )
    )

    assert status == "unavailable"
    assert candidates == []
    assert "not installed" in error


def test_source_lookup_budget_respected(monkeypatch):
    class FakeDDGS:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def text(self, query, max_results=None):
            return [
                {
                    "href": (
                        f"https://jobshot.{index}.com/"
                        "careers"
                    ),
                    "title": f"Careers {query} {index}",
                }
                for index in range(50)
            ]

    monkeypatch.setattr(
        source_discovery,
        "_load_ddgs",
        lambda: (FakeDDGS, None),
    )

    status, candidates, error = (
        source_discovery.discover_sources(
            ["Technical Support Engineer"],
            budget=7,
        )
    )

    assert status == "available"
    assert len(candidates) == 7


def test_irrelevant_search_results_ignored(monkeypatch):
    class FakeDDGS:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def text(self, query, max_results=None):
            return [
                {
                    "href": "https://blog.example.com/post",
                    "title": "Random blog post",
                },
                {
                    "href": "https://news.example.com/story",
                    "title": "News article",
                },
            ]

    monkeypatch.setattr(
        source_discovery,
        "_load_ddgs",
        lambda: (FakeDDGS, None),
    )

    status, candidates, error = (
        source_discovery.discover_sources(
            ["Technical Support Engineer"],
            budget=20,
        )
    )

    assert status == "available"
    assert candidates == []


def test_provider_failure_is_non_fatal(monkeypatch):
    class FakeDDGS:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def text(self, query, max_results=None):
            raise RuntimeError("search backend down")

    monkeypatch.setattr(
        source_discovery,
        "_load_ddgs",
        lambda: (FakeDDGS, None),
    )

    status, candidates, error = (
        source_discovery.discover_sources(
            ["Technical Support Engineer"],
        )
    )

    assert status == "error"
    assert "down" in error


def test_candidates_require_human_approval():
    candidates = source_discovery.classify_candidates(
        [
            {
                "url": "https://boards.greenhouse.io/x",
                "detected_ats": "greenhouse",
                "evidence": "careers",
                "source_query": "q",
                "human_approval_required": True,
            }
        ]
    )

    assert candidates["ats_detected"] == {"greenhouse": 1}
    assert candidates["approved"] == []
    assert candidates["pending_review"][0]["human_approval_required"] is True


# ============================================================
# Profile stays the single source of truth
# ============================================================

def test_round2_vocabulary_aligns_with_profile_priorities():
    for role, family in profile.ROUND2_ROLE_FAMILIES.items():
        assert family in profile.JOB_FAMILY_PRIORITY

    for role in profile.ROUND2_P1_ROLES:
        assert (
            profile.JOB_FAMILY_PRIORITY[
                profile.ROUND2_ROLE_FAMILIES[role]
            ]
            == 1
        )

    for role in profile.ROUND2_P2_ROLES:
        assert (
            profile.JOB_FAMILY_PRIORITY[
                profile.ROUND2_ROLE_FAMILIES[role]
            ]
            == 2
        )


def test_adaptive_loop_disable_flag(monkeypatch):
    monkeypatch.delenv("JOB_AGENT_DISABLE_ADAPTIVE", raising=False)
    assert ai_config.adaptive_discovery_enabled() is True

    monkeypatch.setenv("JOB_AGENT_DISABLE_ADAPTIVE", "1")
    assert ai_config.adaptive_discovery_enabled() is False


def test_adaptive_budgets_are_configurable(monkeypatch):
    assert ai_config.MAX_SEARCH_ROUNDS >= 1
    assert ai_config.MAX_AI_QUERIES >= 1
    assert ai_config.MAX_SOURCE_LOOKUPS >= 1

    monkeypatch.setenv("MAX_AI_QUERIES", "12")

    import importlib

    importlib.reload(ai_config)

    try:
        assert ai_config.MAX_AI_QUERIES == 12
    finally:
        monkeypatch.delenv("MAX_AI_QUERIES")
        importlib.reload(ai_config)


def test_yield_analysis_counts_tiers():
    jobs = [
        make_job(
            "Cloud Support Engineer",
            f"s{index}",
            "Cloud Support",
            description="AWS troubleshooting monitoring",
        )
        for index in range(10)
    ]
    jobs += [
        make_job(
            "DevOps Engineer",
            f"d{index}",
            "DevOps",
            description="AWS Kubernetes",
        )
        for index in range(40)
    ]

    analysis = adaptive_query.analyze_round(jobs)

    assert analysis["total"] == 50
    assert analysis["by_priority"]["P1"] >= 10
    assert analysis["by_priority"]["P3"] >= 40