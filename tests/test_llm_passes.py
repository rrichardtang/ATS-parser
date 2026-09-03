"""The three LLM passes, against a stubbed provider.

No network. What matters here is the wiring: that passes run, that each degrades
on its own, and that a hacked rewrite from a model never reaches the report.
"""
import json

import pytest

from ats import llm, passes, prompts, rubric
from ats.llm import Provider
from ats.models import JUDGED_CATEGORIES, Category, Finding, Gate, Severity
from ats.sections import Resume
from ats.pipeline import RunInput, analyze

# One judge's answers: a placed `no` (the resume says something and what it says is
# the problem), an unplaced `no` (nothing to point at), and a `yes`.
CONTENT_REPLY = json.dumps({
    "categories": {
        "Production ownership": {"criteria": [
            {"id": "C1", "answer": "no", "why": "No bullet names a destination",
             "fix": "Say where it shipped.",
             "evidence": "Leveraged cutting-edge AI technologies",
             "locator": "exp[0].bullet[0]"},
            {"id": "C3", "answer": "no", "why": "Nothing states an operational fact",
             "fix": "Give a load, an incident, or an SLO.",
             "evidence": "", "locator": ""},
            {"id": "C5", "answer": "yes", "why": "the candidate is the subject",
             "evidence": "Leveraged cutting-edge AI technologies",
             "locator": "exp[0].bullet[0]"},
        ]},
        "Resume craft": {"criteria": [
            {"id": "C5", "answer": "no", "why": "This bullet could be anyone's",
             "fix": "Name the system.",
             "evidence": "Leveraged cutting-edge AI technologies",
             "locator": "exp[0].bullet[0]"},
        ]},
    },
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
            rule_id="llm/content", category=Category.RESUME_CRAFT, gate=Gate.MANAGER,
            severity=Severity.MAJOR,
            message="m", fix="f", evidence="e", locator=locator, points=50.0,
        )
        for locator in ["exp[0].heading", *(f"exp[9].bullet[{i}]" for i in range(8))]
    ]
    real = Finding(
        rule_id="llm/content", category=Category.RESUME_CRAFT, gate=Gate.MANAGER,
        severity=Severity.MAJOR,
        message="No outcome", fix="Name the metric.", evidence="Owned GLIDE-ME",
        locator="exp[0].bullet[0]", points=1.0,
    )

    monkeypatch.setattr(llm, "_dispatch", _stub(lambda system: REWRITE_REPLY))
    result = passes.rewrite_pass(
        [Provider("anthropic", "k", "m")], resume, junk + [real],
        objectives=1, samples=1, use_judge=False, margin=1.0, temperature=0.0,
    )

    assert result.meta.get("reason") != "no bullets needed rewriting"


def _answers(*items):
    """items: (category, criterion id, answer, why, evidence, locator)."""
    categories: dict = {}
    for category, cid, answer, why, evidence, locator in items:
        categories.setdefault(category, {"criteria": []})["criteria"].append(
            {"id": cid, "answer": answer, "why": why, "fix": "do it",
             "evidence": evidence, "locator": locator}
        )
    return json.dumps({"categories": categories})


def _one_content_pass(monkeypatch, reply, resume):
    monkeypatch.setattr(llm, "_dispatch", _stub(lambda system: reply))
    return passes.content_pass(
        [Provider("anthropic", "k", "m")], resume, "text", "", [], samples=1,
        temperature=0.0,
    )


def _resume():
    from ats.sections import Role

    return Resume(roles=[Role(heading="Eng", bullets=[
        "Owned GLIDE-ME end to end", "Built a concurrent mapping tool",
    ])])


def test_content_findings_are_keyed_by_the_criterion_they_answer(monkeypatch):
    """The model no longer names the kind of defect; the criterion it answers is the kind.

    That single line -- an id minted from model text -- produced 108 distinct names
    for 198 findings in the baseline. The vocabulary is closed now, and it is the
    specs' own: `<slug>/<criterion id>`.
    """
    reply = _answers(
        ("Production ownership", "C1", "no", "No destination named",
         "Owned GLIDE-ME end to end", "exp[0].bullet[0]"),
        ("Production ownership", "C3", "no", "No operational fact",
         "Built a concurrent mapping tool", "exp[0].bullet[1]"),
    )
    result = _one_content_pass(monkeypatch, reply, _resume())

    assert {f.rule_id for f in result.data} == {
        "production-ownership/C1", "production-ownership/C3",
    }


def test_a_criterion_the_specs_do_not_have_is_dropped(monkeypatch):
    """Exactly as an unevidenced finding is dropped. There is no C9."""
    reply = _answers(
        ("Production ownership", "C9", "no", "invented", "Owned GLIDE-ME end to end",
         "exp[0].bullet[0]"),
        ("Impact & quantification", "C1", "no", "retired category",
         "Owned GLIDE-ME end to end", "exp[0].bullet[0]"),
        ("Production ownership", "C1", "no", "No destination named",
         "Owned GLIDE-ME end to end", "exp[0].bullet[0]"),
    )
    result = _one_content_pass(monkeypatch, reply, _resume())

    assert [f.rule_id for f in result.data] == ["production-ownership/C1"]
    assert [c["criterion_id"] for c in result.meta["unmet"]] == []


def test_a_no_with_nothing_to_point_at_is_an_unmet_criterion_not_a_finding(monkeypatch):
    """The absence case. `/CONTEXT.md` requires a finding to carry a quote, and
    nothing in the resume says any work reached production -- so there is nothing to
    quote and nowhere to point. It is the other object a `no` produces."""
    reply = _answers(
        ("Production ownership", "C1", "no", "Nothing says the work reached anywhere",
         "", ""),
    )
    result = _one_content_pass(monkeypatch, reply, _resume())

    assert result.data == []
    assert [c["criterion_id"] for c in result.meta["unmet"]] == ["production-ownership/C1"]
    assert result.meta["unmet"][0]["message"] == "Nothing says the work reached anywhere"


def test_a_locator_that_resolves_to_nothing_demotes_rather_than_discards(monkeypatch):
    """10% of the baseline's locators named nothing in the parsed resume.

    The reading survives as an unmet criterion; the fictional address does not.
    """
    reply = _answers(
        ("Production ownership", "C1", "no", "No destination named",
         "Owned GLIDE-ME end to end", "exp[9].bullet[4]"),
        ("Production ownership", "C3", "no", "No operational fact",
         "Owned GLIDE-ME end to end", "skills"),
    )
    result = _one_content_pass(monkeypatch, reply, _resume())

    assert result.data == []
    assert {c["criterion_id"] for c in result.meta["unmet"]} == {
        "production-ownership/C1", "production-ownership/C3",
    }


def test_a_criterion_answered_yes_produces_neither_object(monkeypatch):
    """Its quote is the evidence that settles the criterion, not a defect to fix."""
    reply = _answers(
        ("Production ownership", "C1", "yes", "Shipped it",
         "Owned GLIDE-ME end to end", "exp[0].bullet[0]"),
    )
    result = _one_content_pass(monkeypatch, reply, _resume())

    assert result.data == []
    assert result.meta["unmet"] == []
    assert result.meta["criteria_answered"] == 1


def test_an_unreadable_answer_is_dropped_rather_than_read_as_a_no(monkeypatch):
    """A judge that abstains and a judge that answered `no` are not the same thing --
    `rubric.band_of` refuses an incomplete answer set rather than banding one."""
    reply = _answers(
        ("Production ownership", "C1", "maybe", "hedged", "", ""),
    )
    result = _one_content_pass(monkeypatch, reply, _resume())

    assert result.meta["criteria_answered"] == 0
    assert result.data == [] and result.meta["unmet"] == []


def test_two_judges_reporting_one_defect_collide_on_kind_and_place(monkeypatch):
    """10's key of record, now that both halves are closed."""
    def dispatch(provider, system, user, temperature):
        return _answers((
            "Production ownership", "C1", "no",
            "no destination" if provider.name == "anthropic" else "never says where",
            "Owned GLIDE-ME end to end", "exp[0].bullet[0]",
        ))

    monkeypatch.setattr(llm, "_dispatch", dispatch)
    result = passes.content_pass(
        [Provider("anthropic", "k", "m"), Provider("openai", "k", "m")],
        _resume(), "text", "", [], samples=1, temperature=0.0,
    )

    assert len(result.data) == 1


def test_two_judges_splitting_on_a_criterion_produce_a_contested_category(monkeypatch):
    """06's scoring channel, end to end through the pass.

    Both providers answer the same five questions; they differ on C3 alone. The lower
    band wins, the higher one is named, and the split is recorded whether or not it
    moved the band.
    """
    def dispatch(provider, system, user, temperature):
        c3 = "yes" if provider.name == "openai" else "no"
        return _answers(
            ("Production ownership", "C1", "yes", "", "Owned GLIDE-ME end to end",
             "exp[0].bullet[0]"),
            ("Production ownership", "C2", "yes", "", "GLIDE-ME", "exp[0].bullet[0]"),
            ("Production ownership", "C3", c3, "nothing operational",
             "Owned GLIDE-ME end to end", "exp[0].bullet[0]"),
            ("Production ownership", "C4", "no", "no post-launch work", "", ""),
            ("Production ownership", "C5", "yes", "", "Owned GLIDE-ME end to end",
             "exp[0].bullet[0]"),
        )

    monkeypatch.setattr(llm, "_dispatch", dispatch)
    result = passes.content_pass(
        [Provider("anthropic", "k", "m"), Provider("openai", "k", "m")],
        _resume(), "text", "", [], samples=1, temperature=0.0,
    )

    judged = result.judged[Category.PRODUCTION_OWNERSHIP]
    assert judged.judges == 2
    assert (judged.band, judged.value) == ("D", 35.0)
    assert (judged.high_band, judged.high_value) == ("C", 58.0)
    assert judged.contested and judged.gap == 1
    assert judged.split_criteria == ["production-ownership/C3"]
    assert result.meta["contested"] == ["Production ownership"]
    assert result.meta["criterion_splits"] == ["production-ownership/C3"]


def test_a_category_no_judge_answered_completely_gets_no_value(monkeypatch):
    """CONTENT_REPLY answers three of `Production ownership`'s five criteria, so no
    band can be looked up -- and an abstention must not arrive as a low band."""
    result = _one_content_pass(monkeypatch, CONTENT_REPLY, _resume())
    assert Category.PRODUCTION_OWNERSHIP not in result.judged


def test_the_judged_value_reaches_the_report(monkeypatch, fixtures):
    """The whole path: answers -> band -> value -> blend -> composite.

    All five `Production ownership` criteria answered `no` is band E, worth 10, and at
    rule_share 0.4 that is what the category's model half is. Before 06 the category
    showed its rule channel alone.
    """
    def dispatch(provider, system, user, temperature):
        if "ANSWER THE CRITERIA" not in system:
            return _router(system)
        return _answers(*[
            ("Production ownership", f"C{i}", "no", "not evidenced", "", "")
            for i in range(1, 6)
        ])

    monkeypatch.setattr(llm, "_dispatch", dispatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-a")

    report = analyze(RunInput(pdf_path=str(fixtures["strong"]),
                              ensemble_mode="economy", enable_rewrites=False))

    row = next(c for c in report.categories
               if c.category is Category.PRODUCTION_OWNERSHIP)
    assert row.assessed and not row.contested
    # rule_score * 0.4 + 10 * 0.6, so the judged half caps it well under the rule
    # channel's own reading whatever the rules found.
    assert row.score <= 46.0
    assert not any("not wired yet" in note for note in report.notes)


def test_the_content_prompt_asks_the_criteria_and_no_longer_asks_for_a_score():
    system = prompts.content_system()

    assert "MISSING?" not in system, "the open-ended search is what 10 removed"
    assert "Score each category" not in system
    assert '"pattern"' not in system, "the model has no findings vocabulary of its own"
    for slug in rubric.SLUGS:
        spec = rubric.load_spec(slug)
        assert spec["category"] in system
        for criterion in spec["criteria"]:
            assert criterion["question"] in system, f"{slug}/{criterion['id']} not asked"


def test_a_document_whose_roles_did_not_parse_is_withheld(monkeypatch, fixtures):
    """05's rule: every criterion asks about a bullet inside a role, so a document
    whose roles did not survive extraction has its judged categories withheld -- not
    guessed, and not zeroed. The parser gate has already charged for that defect."""
    calls = {"content": 0}

    def dispatch(provider, system, user, temperature):
        if "ANSWER THE CRITERIA" in system:
            calls["content"] += 1
        return _router(system)

    monkeypatch.setattr(llm, "_dispatch", dispatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-a")

    report = analyze(RunInput(pdf_path=str(fixtures["two_column"]),
                              ensemble_mode="economy", enable_rewrites=False))

    assert calls["content"] == 0, "a withheld document must not cost a call"
    assert report.run_meta["pass1"]["withheld"] == [c.value for c in JUDGED_CATEGORIES]
    assert any("withheld" in note for note in report.notes)
    assert not [f for f in report.findings if f.source.startswith("llm:")
                and f.rule_id.startswith("production-ownership/")]
    # 06: and the composite is told, so the three judged categories with a rule
    # channel no longer ride at 100 on a document no parser can read.
    for row in report.categories:
        if row.category in JUDGED_CATEGORIES:
            assert not row.assessed and row.note.startswith("withheld")
    assert sum(c.weight for c in report.categories if c.assessed) == 25.0
