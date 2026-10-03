"""The rewrite harness's logic, with no provider and no network."""
import json
from argparse import Namespace

import pytest

from ats import passes, pipeline, rewrite_eval
from ats.ensemble import PassResult
from ats.llm import Provider
from ats.models import Category, Finding, Gate, Rewrite, Severity
from ats.sections import Resume, Role
from scripts import rewrite_harness as harness

QUOTE = "Leveraged cutting-edge synergies"
BULLET = "Leveraged cutting-edge synergies to ship the thing"
REWRITE = "Shipped the billing service to 4 teams"


def _finding(rule_id, locator="exp[0].bullet[0]"):
    return Finding(rule_id=rule_id, category=Category.RESUME_CRAFT, gate=Gate.MANAGER,
                   severity=Severity.MINOR, message="m", fix="f", evidence=QUOTE,
                   locator=locator)


def _resume(*bullets):
    return Resume(roles=[Role(heading="Eng", bullets=list(bullets))])


def _rewrite(locator="exp[0].bullet[0]", original=BULLET):
    return Rewrite(locator=locator, original=original, rewritten=REWRITE, what_changed="x")


def test_a_rewrite_is_swapped_into_the_resume_and_the_full_text_across_line_breaks():
    text = "Eng\n- Leveraged cutting-edge\n  synergies to ship the thing\nSkills"
    swapped_text, resume, missed = rewrite_eval.swap(text, _resume(BULLET), [_rewrite()])

    assert REWRITE in swapped_text and "synergies" not in swapped_text
    assert resume.bullets == [("exp[0].bullet[0]", REWRITE)]
    assert missed == set()


def test_an_original_missing_from_the_text_is_left_alone_and_reported():
    other = _rewrite("exp[0].bullet[1]", "Not in the text at all")
    original = _resume(BULLET, other.original)
    text, resume, missed = rewrite_eval.swap(BULLET, original, [other])

    assert (text, missed) == (BULLET, {"exp[0].bullet[1]"})
    assert resume.bullets == original.bullets


def _classify(handed, rewrites, selections=(), missed=(), after=(), measured=True, kinds=None):
    kinds = kinds or {(f.locator, f.rule_id): "content" for _, items in handed for f in items}
    entries = rewrite_eval.classify(handed, kinds, rewrites, list(selections), set(missed),
                                    set(after), measured)
    return {(e["rule_id"], e["locator"]): (e["outcome"], e["reason"]) for e in entries}


def test_fixed_not_fixed_and_not_swapped():
    loc = "exp[0].bullet[0]"
    handed = [(loc, [_finding("a"), _finding("b")])]
    assert _classify(handed, [_rewrite()], after={(loc, "b")}) == {
        ("a", loc): ("fixed", ""), ("b", loc): ("not_fixed", "")}
    assert _classify(handed, [_rewrite()], missed={loc}) == {
        ("a", loc): ("not_swapped", ""), ("b", loc): ("not_swapped", "")}


@pytest.mark.parametrize("selection, reason", [
    ({"locator": "exp[0].bullet[0]", "reason": "no candidates"}, "no candidates"),
    ({"locator": "exp[0].bullet[0]",
      "reason": "no candidate beat the original without regressing"}, "no margin"),
    ({"locator": "exp[0].bullet[0]", "reason": "no candidate beat the original without "
      "regressing", "rejected_for_audit": [{"problems": ["invented 62%"]}]}, "audit rejected"),
    (None, "no selection"),
])
def test_not_shipped_carries_a_reason_that_quotes_nothing(selection, reason):
    handed = [("exp[0].bullet[0]", [_finding("a")])]
    outcome = _classify(handed, [], [selection] if selection else [])
    assert outcome == {("a", "exp[0].bullet[0]"): ("not_shipped", reason)}


def test_slop_pass_findings_and_an_unjudged_content_rerun_are_unmeasured():
    loc = "exp[0].bullet[0]"
    handed = [(loc, [_finding("slop/x"), _finding("c")])]
    kinds = {(loc, "c"): "content"}
    assert _classify(handed, [_rewrite()], kinds=kinds, measured=False) == {
        ("slop/x", loc): ("unmeasured", ""), ("c", loc): ("unmeasured", "")}


def test_the_control_counts_findings_that_vanish_with_no_edit():
    before = [_finding("a"), _finding("b"), _finding("c", "exp[0].bullet[1]")]
    control = [_finding("a"), _finding("z")]
    assert rewrite_eval.control_counts(before, control) == {"findings": 3, "vanished": 2}


def _document(name, *targets, control=None):
    return {"name": name, "control": control,
            "targets": [{"locator": "exp[0].bullet[0]", "rule_id": "r", "reason": "",
                         "evidence": QUOTE, **t} for t in targets]}


RUN = {"documents": [
    _document("one", {"kind": "deterministic", "outcome": "fixed"},
              {"kind": "content", "outcome": "fixed"},
              {"kind": "content", "outcome": "not_shipped", "reason": "no margin"},
              control={"findings": 4, "vanished": 1}),
    _document("two", {"kind": "content", "outcome": "not_fixed"},
              control={"findings": 4, "vanished": 1}),
    {"name": "three", "skipped": "no text layer"},
]}


def test_tally_and_table_split_kinds_and_report_the_control_beside_the_fix_rate():
    total = rewrite_eval.tally(RUN["documents"])
    assert total["outcomes"]["content"] == {"fixed": 1, "not_shipped": 1, "not_fixed": 1}
    assert total["control"] == {"findings": 8, "vanished": 2}
    assert total["not_shipped_reasons"] == {"no margin": 1}

    table = rewrite_eval.render(RUN)
    assert "2 of 8 content findings vanished (25%)" in table
    assert "(50%)" in table and "no margin 1" in table and "three: no text layer" in table
    assert QUOTE not in table


def test_the_summary_holds_no_bullet_or_quote_text():
    out = json.dumps(rewrite_eval.summary(
        {"documents": [{**RUN["documents"][0], "rewrites": [_rewrite().model_dump()]},
                       RUN["documents"][2]]}))
    assert "Leveraged" not in out and "evidence" not in out and "rewrite" not in out
    assert "exp[0].bullet[0]" in out and "no text layer" in out


def test_the_dry_run_counts_calls_per_document():
    settings = {"content_votes": 3, "slop_samples": 3, "rewrite_objectives": 3,
                "rewrite_samples": 2, "rewrite_judge": True}
    assert sum(rewrite_eval.call_counts(settings).values()) == 9 + 3 + 6 + 2
    assert sum(rewrite_eval.call_counts({**settings, "rewrite_judge": False}).values()) == 18


def test_a_dry_run_prints_calls_and_cost_without_a_key(monkeypatch, capsys):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr("sys.argv", ["h", "--docs", "strong", "--dry-run",
                                     "--openai-price", "0.10,0.50"])
    harness.main()
    out = capsys.readouterr().out
    assert "1 resume(s) x (9 content + 3 slop + 3 rewrite + 2 judge and polish) = up to 17" in out
    assert "Worst case $" in out and "budget" in out


def test_a_live_run_without_the_key_exits_naming_it(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr("sys.argv", ["h", "--docs", "strong"])
    with pytest.raises(SystemExit, match="OPENAI_API_KEY"):
        harness.main()


def test_over_budget_sends_nothing(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "k")
    monkeypatch.setattr(rewrite_eval, "evaluate", lambda *a: pytest.fail("sent"))
    monkeypatch.setattr("sys.argv", ["h", "--docs", "strong", "--budget", "0.001",
                                     "--openai-price", "0.10,0.50"])
    with pytest.raises(SystemExit, match="over budget"):
        harness.main()


def test_evaluate_runs_before_control_and_after_against_stubbed_passes(monkeypatch, fixtures):
    calls = []

    def content(providers, resume, text, jd, deterministic, votes, temperature, digest):
        calls.append(text)
        # first asking and the control find a content defect; after the swap it is gone
        defect = [] if REWRITE in text else [_finding("content/x")]
        return PassResult(data=defect)

    resume = harness.parse(harness.extract(str(fixtures["slop"])).text)
    BULLET_TEXT = resume.bullets[0][1]
    shipped = Rewrite(locator="exp[0].bullet[0]", original=BULLET_TEXT, rewritten=REWRITE,
                      what_changed="x")
    monkeypatch.setattr(pipeline, "deterministic", lambda *a: [])
    monkeypatch.setattr(passes, "content_pass", content)
    monkeypatch.setattr(passes, "slop_pass", lambda *a: PassResult())
    monkeypatch.setattr(passes, "rewrite_pass", lambda *a: PassResult(data=[shipped]))
    provider = Provider("openai", "-", "m")

    record = rewrite_eval.evaluate("slop", str(fixtures["slop"]), [provider], [provider],
                                   {"content_votes": 3, "temperature": 0.7, "slop_samples": 3,
                                    "slop_vote_k": 2, "rewrite_objectives": 3,
                                    "rewrite_samples": 1, "rewrite_judge": True,
                                    "rewrite_margin": 1.0})

    assert len(calls) == 3 and REWRITE in calls[2] and REWRITE not in calls[1]
    assert record["control"] == {"findings": 1, "vanished": 0}
    fixed = {(t["rule_id"], t["outcome"]) for t in record["targets"]}
    assert ("content/x", "fixed") in fixed
