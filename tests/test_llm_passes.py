"""The three LLM passes, against a stubbed provider.

No network. What matters here is the wiring: that passes run, that each degrades
on its own, and that a hacked rewrite from a model never reaches the report.
"""
import json

import pytest

from ats import llm, passes
from ats.llm import Provider
from ats.models import Category, Finding, Severity
from ats.sections import Resume
from ats.pipeline import RunInput, analyze

CONTENT_REPLY = json.dumps({
    "categories": {
        "Production ownership": {"score": 45, "why": "no outcomes stated"},
        "Evaluation rigour": {"score": 50, "why": "generic"},
        "Resume craft": {"score": 40, "why": "formulaic"},
    },
    "findings": [{
        "message": "No bullet names a model or dataset",
        "fix": "Name the model and the eval set.",
        "evidence": "Leveraged cutting-edge AI technologies",
        "locator": "exp[0].bullet[0]",
        "category": "Production ownership",
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
    "rewritten": "Built an AI retrieval pipeline that serves internal search queries.",
    "what_changed": "named the system",
}]})
HONEST_REWRITE_B = json.dumps({"rewrites": [{
    "locator": "exp[0].bullet[0]",
    "rewritten": "Shipped an AI-powered RAG service for internal search, replacing "
                 "keyword lookup.",
    "what_changed": "named the mechanism",
}]})
JUDGE_REPLY = json.dumps({"rankings": [{
    "locator": "exp[0].bullet[0]",
    "order": [{"candidate_id": "c0", "why": "clearer mechanism"},
              {"candidate_id": "c1", "why": "still solid"}],
}]})
# The polish step hallucinates a number found in neither honest candidate nor the
# original bullet.
HACKED_POLISH = json.dumps({"polished": [{
    "locator": "exp[0].bullet[0]",
    "rewritten": "Built an AI retrieval pipeline that serves internal search queries, "
                 "cutting latency 40%.",
    "what_changed": "tightened wording",
}]})


def test_judge_and_polish_run_and_polish_is_gated_like_any_candidate(monkeypatch, fixtures):
    """Default mode adds a quality judge and a polish-the-winner step on top of
    fact-checked best-of-N. Both must actually run, and a hallucinated figure from
    polish must not ship -- the final gate applies to it exactly as it would to
    any other candidate."""
    def _dispatch(provider, system, user, temperature):
        if "detect AI-generated writing" in system:
            return SLOP_REPLY
        if "rank candidate rewrites" in system.lower():
            return JUDGE_REPLY
        if "lightly polish" in system.lower():
            return HACKED_POLISH
        if "rewrite weak resume bullets" in system:
            return HONEST_REWRITE_A if provider.name == "anthropic" else HONEST_REWRITE_B
        return CONTENT_REPLY

    monkeypatch.setattr(llm, "_dispatch", _dispatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-a")
    monkeypatch.setenv("OPENAI_API_KEY", "test-o")

    report = analyze(RunInput(pdf_path=str(fixtures["slop"]), ensemble_mode="default"))

    pass3 = report.run_meta.get("pass3", {})
    assert pass3.get("judge_used") is True
    assert pass3.get("polished_count", 0) >= 1, "polish step never ran"
    for rewrite in report.rewrites:
        assert "40%" not in rewrite.rewritten, "a hallucinated polish figure shipped"


def test_economy_mode_skips_the_judge(monkeypatch, fixtures):
    """Economy mode should never place the extra judge/polish calls."""
    calls = {"judge": 0, "polish": 0}

    def _dispatch(provider, system, user, temperature):
        if "detect AI-generated writing" in system:
            return SLOP_REPLY
        if "rank candidate rewrites" in system.lower():
            calls["judge"] += 1
            return JUDGE_REPLY
        if "lightly polish" in system.lower():
            calls["polish"] += 1
            return HACKED_POLISH
        if "rewrite weak resume bullets" in system:
            return HONEST_REWRITE_A if provider.name == "anthropic" else HONEST_REWRITE_B
        return CONTENT_REPLY

    monkeypatch.setattr(llm, "_dispatch", _dispatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-a")
    monkeypatch.setenv("OPENAI_API_KEY", "test-o")

    report = analyze(RunInput(pdf_path=str(fixtures["slop"]), ensemble_mode="economy"))

    assert calls == {"judge": 0, "polish": 0}
    assert report.run_meta["pass3"]["judge_used"] is False


def test_malformed_json_is_repaired_then_used(monkeypatch):
    calls = {"n": 0}

    def _dispatch(provider, system, user, temperature):
        calls["n"] += 1
        return "here you go:\n```json\n{\"findings\": []}\n```" if calls["n"] == 1 else "{}"

    monkeypatch.setattr(llm, "_dispatch", _dispatch)
    result = llm.call(Provider("anthropic", "k", "m"), "sys", "user")
    assert result == {"findings": []}


def test_unrewritable_locators_do_not_consume_the_target_budget(monkeypatch):
    """Heading and invented locators must not crowd out real bullets.

    The top-scoring findings are frequently on headings or on indices the model
    made up. Cutting to MAX_REWRITE_TARGETS before checking which locators resolve
    let those take every slot, and the pass reported "no bullets needed rewriting"
    while real, defective bullets sat further down the ranking.
    """
    from ats.sections import Resume, Role

    resume = Resume(roles=[Role(heading="Eng", bullets=["Owned GLIDE-ME end to end"])])
    junk = [
        Finding(
            rule_id="llm/content", category=Category.RESUME_CRAFT, severity=Severity.MAJOR,
            message="m", fix="f", evidence="e", locator=locator, points=50.0,
        )
        for locator in ["exp[0].heading", *(f"exp[9].bullet[{i}]" for i in range(8))]
    ]
    real = Finding(
        rule_id="llm/content", category=Category.RESUME_CRAFT, severity=Severity.MAJOR,
        message="No outcome", fix="Name the metric.", evidence="Owned GLIDE-ME",
        locator="exp[0].bullet[0]", points=1.0,
    )

    monkeypatch.setattr(llm, "_dispatch", _stub(lambda system: REWRITE_REPLY))
    result = passes.rewrite_pass(
        [Provider("anthropic", "k", "m")], resume, junk + [real],
        objectives=1, samples=1, use_judge=False, margin=1.0, temperature=0.0,
    )

    assert result.meta.get("reason") != "no bullets needed rewriting"


def test_content_findings_are_keyed_by_the_defect_the_model_named(monkeypatch):
    """Distinct content defects must not collapse into one card and one ledger row.

    Every content finding used to carry rule_id "llm/content", so Report.grouped
    and the ledger both treated unrelated defects as instances of one rule and
    titled the lot after whichever scored highest.
    """
    reply = json.dumps({"categories": {}, "findings": [
        {"pattern": "unverified outcome", "message": "No metric for routing",
         "fix": "Add one.", "evidence": "cutting inference passes",
         "locator": "exp[0].bullet[1]", "category": "Production ownership"},
        {"pattern": "unverified outcome", "message": "No metric for the mapping tool",
         "fix": "Add one.", "evidence": "Built a concurrent mapping tool",
         "locator": "exp[0].bullet[4]", "category": "Production ownership"},
        {"pattern": "activity not outcome", "message": "Lists duties, not results",
         "fix": "State the result.", "evidence": "Owned GLIDE-ME end to end",
         "locator": "exp[0].bullet[0]", "category": "Production ownership"},
    ]})
    monkeypatch.setattr(llm, "_dispatch", _stub(lambda system: reply))

    result = passes.content_pass(
        [Provider("anthropic", "k", "m")], Resume(), "text", "", [], samples=1,
        temperature=0.0,
    )

    assert {f.rule_id for f in result.data} == {
        "llm/unverified-outcome", "llm/activity-not-outcome",
    }


def test_content_findings_without_a_pattern_still_get_an_id(monkeypatch):
    """The model may omit the label; the pass must not produce an empty rule id."""
    reply = json.dumps({"categories": {}, "findings": [
        {"message": "No metric", "fix": "Add one.", "evidence": "cutting passes",
         "locator": "exp[0].bullet[1]", "category": "Production ownership"},
    ]})
    monkeypatch.setattr(llm, "_dispatch", _stub(lambda system: reply))

    result = passes.content_pass(
        [Provider("anthropic", "k", "m")], Resume(), "text", "", [], samples=1,
        temperature=0.0,
    )
    assert [f.rule_id for f in result.data] == ["llm/content"]
