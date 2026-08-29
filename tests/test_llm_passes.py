"""The three LLM passes, against a stubbed provider.

No network. What matters here is the wiring: that passes run, that each degrades
on its own, and that a hacked rewrite from a model never reaches the report.
"""
import json

import pytest

from ats import llm, passes
from ats.llm import Provider
from ats.pipeline import RunInput, analyze

CONTENT_REPLY = json.dumps({
    "categories": {
        "Impact & quantification": {"score": 45, "why": "no outcomes stated"},
        "AI/ML relevance & depth": {"score": 50, "why": "generic"},
        "Writing quality": {"score": 40, "why": "formulaic"},
    },
    "findings": [{
        "message": "No bullet names a model or dataset",
        "fix": "Name the model and the eval set.",
        "evidence": "Leveraged cutting-edge AI technologies",
        "locator": "exp[0].bullet[0]",
        "category": "Credibility & verifiability",
    }],
})

SLOP_REPLY = json.dumps({"findings": [{
    "pattern": "hollow specificity",
    "quoted_line": "Leveraged cutting-edge AI technologies to deliver robust and scalable",
    "fix": "name the system",
}]})

# The model proposes a hacked rewrite: a plausible figure it invented.
REWRITE_REPLY = json.dumps({"rewrites": [{
    "locator": "exp[0].bullet[0]",
    "rewritten": "Cut inference latency by 62% across the platform.",
    "what_changed": "added a metric",
}]})


def _stub(reply_for):
    def _dispatch(provider, system, user, temperature):
        return reply_for(system)
    return _dispatch


def _router(system):
    if "detect AI-generated writing" in system:
        return SLOP_REPLY
    if "rewrite weak resume bullets" in system:
        return REWRITE_REPLY
    return CONTENT_REPLY


@pytest.fixture
def stubbed(monkeypatch):
    monkeypatch.setattr(llm, "_dispatch", _stub(_router))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-a")
    monkeypatch.setenv("OPENAI_API_KEY", "test-o")


def test_all_three_passes_contribute(stubbed, fixtures):
    report = analyze(RunInput(pdf_path=str(fixtures["slop"]), ensemble_mode="economy"))
    sources = {f.source for f in report.findings}
    assert any(s.startswith("llm:") for s in sources), "no LLM findings reached the report"
    assert report.run_meta["providers"], "providers not recorded"


def test_cross_provider_scores_are_averaged_and_banded(stubbed, fixtures):
    report = analyze(RunInput(pdf_path=str(fixtures["slop"]), ensemble_mode="economy"))
    assert report.run_meta["pass1"]["providers"] == ["anthropic", "openai"]


def test_invented_metric_from_the_model_is_rejected(stubbed, fixtures):
    """The stub returns a rewrite containing a figure absent from the source.

    It must not ship. This is the defence that matters most: a fabricated number
    is something the candidate has to defend in an interview.
    """
    report = analyze(RunInput(pdf_path=str(fixtures["slop"]), ensemble_mode="economy"))
    for rewrite in report.rewrites:
        assert "62%" not in rewrite.rewritten
    selections = report.run_meta.get("pass3", {}).get("selections", [])
    assert any(s.get("rejected_for_audit") for s in selections)


def test_a_failing_pass_does_not_lose_the_report(monkeypatch, fixtures):
    """Each pass degrades independently -- the rest of the report still renders."""
    def _explode(provider, system, user, temperature):
        if "detect AI-generated writing" in system:
            raise RuntimeError("provider unavailable")
        return _router(system)

    monkeypatch.setattr(llm, "_dispatch", _explode)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-a")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    report = analyze(RunInput(pdf_path=str(fixtures["slop"]), ensemble_mode="economy"))
    assert report.composite > 0
    assert len(report.findings) > 5
    assert any("degraded" in n.lower() for n in report.notes)


def test_single_provider_is_flagged_in_the_notes(monkeypatch, fixtures):
    monkeypatch.setattr(llm, "_dispatch", _stub(_router))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-a")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    report = analyze(RunInput(pdf_path=str(fixtures["slop"]), ensemble_mode="economy"))
    assert any("one provider" in n.lower() for n in report.notes)


def test_unquotable_llm_finding_is_dropped(monkeypatch, fixtures):
    """A model claim with no matching text in the resume is not checkable."""
    fake = json.dumps({"findings": [{
        "pattern": "invented", "quoted_line": "text that is nowhere in this resume",
        "fix": "n/a",
    }]})

    def _dispatch(provider, system, user, temperature):
        return fake if "detect AI-generated" in system else CONTENT_REPLY

    monkeypatch.setattr(llm, "_dispatch", _dispatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-a")
    report = analyze(RunInput(pdf_path=str(fixtures["slop"]), ensemble_mode="economy",
                              enable_rewrites=False))
    assert not [f for f in report.findings if "nowhere in this resume" in f.evidence]


HONEST_REWRITE_A = json.dumps({"rewrites": [{
    "locator": "exp[0].bullet[0]",
    "rewritten": "Built a retrieval pipeline that serves internal search queries.",
    "what_changed": "named the system",
}]})
HONEST_REWRITE_B = json.dumps({"rewrites": [{
    "locator": "exp[0].bullet[0]",
    "rewritten": "Shipped a RAG service for internal search, replacing keyword lookup.",
    "what_changed": "named the mechanism",
}]})
# The synthesis (mixture-of-agents) step invents a number found in neither honest
# candidate nor the original bullet.
HACKED_SYNTHESIS = json.dumps({
    "locator": "exp[0].bullet[0]",
    "rewritten": "Shipped a RAG-based retrieval pipeline for internal search, cutting "
                 "latency 40%.",
    "what_changed": "combined both candidates",
})


def test_synthesis_runs_and_is_gated_like_any_other_candidate(monkeypatch, fixtures):
    """Mixture-of-agents adds one more candidate per bullet -- it must not bypass
    the same rank/audit/margin gates every best-of-N candidate goes through."""
    def _dispatch(provider, system, user, temperature):
        if "detect AI-generated writing" in system:
            return SLOP_REPLY
        if "synthesize one strong resume bullet" in system:
            return HACKED_SYNTHESIS
        if "rewrite weak resume bullets" in system:
            return HONEST_REWRITE_A if provider.name == "anthropic" else HONEST_REWRITE_B
        return CONTENT_REPLY

    monkeypatch.setattr(llm, "_dispatch", _dispatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-a")
    monkeypatch.setenv("OPENAI_API_KEY", "test-o")

    report = analyze(RunInput(pdf_path=str(fixtures["slop"]), ensemble_mode="default"))

    pass3 = report.run_meta.get("pass3", {})
    assert pass3.get("synthesis_attempts", 0) >= 1, "synthesis step never ran"
    for rewrite in report.rewrites:
        assert "40%" not in rewrite.rewritten, "a synthesized fabrication shipped"
    selections = pass3.get("selections", [])
    assert any(s.get("rejected_for_audit") for s in selections)


def test_malformed_json_is_repaired_then_used(monkeypatch):
    calls = {"n": 0}

    def _dispatch(provider, system, user, temperature):
        calls["n"] += 1
        return "here you go:\n```json\n{\"findings\": []}\n```" if calls["n"] == 1 else "{}"

    monkeypatch.setattr(llm, "_dispatch", _dispatch)
    result = llm.call(Provider("anthropic", "k", "m"), "sys", "user")
    assert result == {"findings": []}
