"""The rewrite harness's logic, with no provider and no network."""
import json
import threading
import time
from argparse import Namespace
from concurrent.futures import ThreadPoolExecutor

import pytest

from ats import passes, pipeline, rewrite_eval
from ats.ensemble import PassResult
from ats.llm import Provider
from ats.models import Category, Finding, Gate, Rewrite, Severity
from ats.sections import Resume, Role
from scripts import rewrite_harness as harness
from scripts.agreement_harness import acceptance_targets

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
    ({"locator": "exp[0].bullet[0]", "reason": "audit rejected"}, "audit rejected"),
    ({"locator": "exp[0].bullet[0]", "reason": "new defect"}, "new defect"),
    ({"locator": "exp[0].bullet[0]", "reason": "fixed nothing"}, "fixed nothing"),
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
    measured = {("exp[0].bullet[0]", "a"), ("exp[0].bullet[0]", "b"),
                ("exp[0].bullet[1]", "c")}
    control = [_finding("a"), _finding("z")]
    assert rewrite_eval.control_counts(measured, control) == {"findings": 3, "vanished": 2}


def test_swap_text_refuses_a_substring_or_a_repeated_original():
    assert rewrite_eval.swap_text("- Led team of 5 engineers\n- Led team\n", "Led team",
                                  "NEW") is None
    assert rewrite_eval.swap_text("The Ledger closed", "Led", "NEW") is None
    assert rewrite_eval.swap_text("- Led team of 5\n- Led team\n", "Led team of 5",
                                  "NEW") == "- NEW\n- Led team\n"


def _document(name, *targets, control=None):
    return {"name": name, "control": control,
            "targets": [{"locator": "exp[0].bullet[0]", "rule_id": "r", "reason": "",
                         "evidence": QUOTE, **t} for t in targets]}


RUN = {"documents": [
    _document("one", {"kind": "deterministic", "outcome": "fixed"},
              {"kind": "content", "outcome": "fixed"},
              {"kind": "content", "outcome": "not_shipped", "reason": "fixed nothing"},
              control={"findings": 4, "vanished": 1}),
    _document("two", {"kind": "content", "outcome": "not_fixed"},
              control={"findings": 4, "vanished": 1}),
    {"name": "three", "skipped": "no text layer"},
]}


def test_tally_and_table_split_kinds_and_report_the_control_beside_the_fix_rate():
    total = rewrite_eval.tally(RUN["documents"])
    assert total["outcomes"]["content"] == {"fixed": 1, "not_shipped": 1, "not_fixed": 1}
    assert total["control"] == {"findings": 8, "vanished": 2}
    assert total["not_shipped_reasons"] == {"fixed nothing": 1}

    table = rewrite_eval.render(RUN)
    assert "2 of 8 content findings vanished (25%)" in table
    assert "(50%)" in table and "fixed nothing 1" in table and "three: no text layer" in table
    assert QUOTE not in table


def test_the_summary_holds_no_bullet_or_quote_text():
    out = json.dumps(rewrite_eval.summary(
        {"documents": [{**RUN["documents"][0], "rewrites": [_rewrite().model_dump()]},
                       RUN["documents"][2]]}))
    assert "Leveraged" not in out and "evidence" not in out and "rewrite" not in out
    slop = {**RUN["documents"][0]["targets"][0], "kind": "slop", "rule_id": "slop/jane-doe"}
    assert "jane-doe" not in json.dumps(rewrite_eval.summary(
        {"documents": [{"name": "d", "targets": [slop]}]}))
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
    assert "Worst case $" in out and "no document starts" in out


def test_a_live_run_without_the_key_exits_naming_it(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr("sys.argv", ["h", "--docs", "strong"])
    with pytest.raises(SystemExit, match="OPENAI_API_KEY"):
        harness.main()


def test_a_document_whose_worst_case_is_over_budget_sends_nothing(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "k")
    monkeypatch.setattr(rewrite_eval, "evaluate", lambda *a: pytest.fail("sent"))
    monkeypatch.setattr("sys.argv", ["h", "--docs", "strong", "--budget", "0.001",
                                     "--openai-price", "0.10,0.50"])
    with pytest.raises(SystemExit, match="over the"):
        harness.main()


def test_evaluate_runs_before_control_and_after_against_stubbed_passes(monkeypatch, fixtures):
    calls = []

    def content(providers, resume, text, jd, deterministic, votes, temperature, digest):
        calls.append(text)
        # first asking and the control find a content defect; after the swap it is gone
        defect = [] if REWRITE in text else [_finding("content/x", shipped.locator)]
        return PassResult(data=defect)

    shipped = _rewrite_for(fixtures)
    monkeypatch.setattr(pipeline, "deterministic", lambda *a: [])
    monkeypatch.setattr(passes, "content_pass", content)
    monkeypatch.setattr(passes, "slop_pass", lambda *a: PassResult())
    monkeypatch.setattr(passes, "rewrite_pass", lambda *a: PassResult(data=[shipped]))
    provider = Provider("openai", "-", "m")

    record = rewrite_eval.evaluate("strong", str(fixtures["strong"]), [provider], [provider],
                                   {"content_votes": 3, "temperature": 0.7, "slop_samples": 3,
                                    "slop_vote_k": 2, "rewrite_objectives": 3,
                                    "rewrite_samples": 1, "rewrite_judge": True})

    assert len(calls) == 3 and REWRITE in calls[2] and REWRITE not in calls[1]
    assert record["control"] == {"findings": 1, "vanished": 0}  # fix-rate set only
    fixed = {(t["rule_id"], t["outcome"]) for t in record["targets"]}
    assert ("content/x", "fixed") in fixed


def test_a_failed_control_leaves_content_outcomes_unmeasured(monkeypatch, fixtures):
    monkeypatch.setattr(pipeline, "deterministic", lambda *a: [])
    runs = iter([PassResult(data=[_finding("c", _rewrite_for(fixtures).locator)]), PassResult(errors=["boom"]), PassResult()])
    monkeypatch.setattr(passes, "content_pass", lambda *a: next(runs))
    monkeypatch.setattr(passes, "slop_pass", lambda *a: PassResult())
    monkeypatch.setattr(passes, "rewrite_pass", lambda *a: PassResult(data=[_rewrite_for(fixtures)]))
    provider = Provider("openai", "-", "m")
    record = rewrite_eval.evaluate("strong", str(fixtures["strong"]), [provider], [provider],
                                   {"content_votes": 3, "temperature": 0.7, "slop_samples": 3,
                                    "slop_vote_k": 2, "rewrite_objectives": 3,
                                    "rewrite_samples": 1, "rewrite_judge": True})
    assert record["control"] is None
    assert {t["outcome"] for t in record["targets"]} == {"unmeasured"}


def _rewrite_for(fixtures):
    locator, original = _unique_bullet(fixtures)
    return Rewrite(locator=locator, original=original, rewritten=REWRITE, what_changed="x")


def _unique_bullet(fixtures):
    """A bullet that occurs once in the strong fixture (a repeated one cannot swap)."""
    text = harness.extract(str(fixtures["strong"])).text
    bullets = harness.parse(text).bullets
    return next((loc, b) for loc, b in bullets
                if rewrite_eval.swap_text(text, b, "x") is not None)


def test_a_resume_is_summarised_under_a_fixed_label_not_its_file_stem(monkeypatch, fixtures,
                                                                      tmp_path):
    named = tmp_path / "Jane_Doe_Resume.pdf"
    named.write_bytes(fixtures["strong"].read_bytes())
    seen = []
    monkeypatch.setenv("OPENAI_API_KEY", "k")
    monkeypatch.setattr(rewrite_eval, "evaluate",
                        lambda name, *a: seen.append(name) or {"name": name, "skipped": "x"})
    monkeypatch.setattr("sys.argv", ["h", "--docs", "Jane_Doe_Resume", "--resume", str(named),
                                     "--out", str(tmp_path / "run.json"), "--budget", "99",
                                     "--openai-price", "0.10,0.50"])
    harness.main()
    assert seen == ["resume"]


def _usage(prompt, cached, output, reasoning=0):
    from types import SimpleNamespace as NS

    return NS(prompt_tokens=prompt, completion_tokens=output,
              prompt_tokens_details=NS(cached_tokens=cached),
              completion_tokens_details=NS(reasoning_tokens=reasoning))


def _record(tokens, seconds=0.0):
    from ats import llm

    llm._log_openai_usage(Provider("openai", "k", "m"), _usage(*tokens), "stop", seconds)


def test_usage_accumulator_sums_concurrent_records():
    from concurrent.futures import ThreadPoolExecutor

    from ats import llm

    llm.take_usage()
    with ThreadPoolExecutor(8) as pool:
        list(pool.map(lambda i: _record((10, 4, 3, 1), seconds=i / 100), range(400)))
    assert llm.take_usage() == {"input": 4000, "cached": 1600, "output": 1200,
                                "reasoning": 400, "slowest_seconds": 3.99}
    assert llm.take_usage()["input"] == 0


def test_usage_is_kept_per_key_through_gather_threads():
    from ats import ensemble, llm

    def document(key):
        llm.usage_key.set(key)
        ensemble.gather([lambda: _record((key, 0, 1))] * 3)

    with ThreadPoolExecutor(2) as pool:
        list(pool.map(document, (100, 200)))
    assert (llm.take_usage(100)["input"], llm.take_usage(200)["input"]) == (300, 600)


def test_an_openai_call_records_its_seconds_and_reasoning_tokens(monkeypatch):
    from types import SimpleNamespace as NS

    from ats import llm

    clock = iter([10.0, 12.5])
    reply = NS(usage=_usage(100, 0, 40, 30),
               choices=[NS(finish_reason="stop", message=NS(content="{}"))])
    client = NS(chat=NS(completions=NS(create=lambda **_: reply)))
    monkeypatch.setattr(llm, "_openai_client", lambda *a: client)
    monkeypatch.setattr(llm, "time", NS(monotonic=lambda: next(clock)))
    llm.take_usage()
    assert llm.call(Provider("openai", "k", "m"), "s", "u") == {}
    assert llm.take_usage() == {"input": 100, "cached": 0, "output": 40, "reasoning": 30,
                                "slowest_seconds": 2.5}


def _stub_run(monkeypatch, tmp_path, *args, tokens=(1_000_000, 0, 0), errors=None,
              evaluate=None):
    """Run main() live with evaluate stubbed (by default, to record `tokens` per document)."""
    seen = []

    def stub(name, *a):
        seen.append(name)
        _record(tokens)
        return {"name": name, "targets": [], "errors": errors or {}}

    monkeypatch.setenv("OPENAI_API_KEY", "k")
    monkeypatch.setattr(rewrite_eval, "evaluate", evaluate or stub)
    monkeypatch.setattr("sys.argv", ["h", "--out", str(tmp_path / "run.json"),
                                     "--openai-price", "1,1", *args])
    harness.main()
    return seen, json.loads((tmp_path / "run.json").read_text())


def test_the_guard_stops_before_a_document_that_could_pass_the_budget(monkeypatch, tmp_path,
                                                                     capsys):
    monkeypatch.setattr(rewrite_eval, "worst_case", lambda *a: 1.5)
    seen, run = _stub_run(monkeypatch, tmp_path, "--docs", "strong,slop,two_column", "--budget", "2.0")
    assert seen == ["strong"]
    assert run["skipped_for_budget"] == ["slop", "two_column"]
    assert run["documents"][0]["spend"]["dollars"] == 1.0
    out = capsys.readouterr().out
    assert "2 document(s) skipped" in out and "$1.00 charged so far" in out
    assert "Real spend: 1000000 input" in out


def test_real_spend_is_in_the_raw_run_and_the_summary(monkeypatch, tmp_path):
    monkeypatch.setattr(rewrite_eval, "worst_case", lambda *a: 0.1)
    _, run = _stub_run(monkeypatch, tmp_path, "--docs", "strong", "--budget", "5",
                       tokens=(2000, 500, 100))
    assert run["documents"][0]["spend"] == {"input": 2000, "cached": 500, "output": 100,
                                            "reasoning": 0, "dollars": 0.0021}
    assert run["documents"][0]["charged"] == 0.0021
    assert rewrite_eval.summary(run)["spend"]["output"] == 100


def test_no_fixtures_selects_exactly_the_drawn_documents(monkeypatch, tmp_path):
    monkeypatch.setattr(rewrite_eval, "worst_case", lambda *a: 0.0)
    seen, _ = _stub_run(monkeypatch, tmp_path, "--acceptance-set", "--no-fixtures",
                        "--budget", "5", tokens=(0, 0, 0))
    drawn = {name for name, _ in acceptance_targets()}
    assert len(seen) == 30 and set(seen) == drawn


def test_a_document_with_failed_calls_is_charged_its_worst_case(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(rewrite_eval, "worst_case", lambda *a: 1.5)
    seen, run = _stub_run(monkeypatch, tmp_path, "--docs", "strong,slop,two_column",
                          "--budget", "2.9", errors={"before": ["timed out"]})
    assert seen == ["strong"]
    assert run["documents"][0]["spend"]["dollars"] == 1.0
    assert run["documents"][0]["charged"] == 1.5
    assert "$1.50 charged so far" in capsys.readouterr().out


DOCS = "strong,slop,two_column,no_phone,buried_evidence"


def _staggered(name, *a):
    """A record that depends only on the name, finishing out of target order."""
    time.sleep({"strong": 0.004, "slop": 0.001}.get(name, 0.002))
    _record((len(name) * 1000, 0, len(name) * 10, len(name)))
    return {"name": name, "targets": [{"locator": name, "rule_id": "r", "kind": "content",
                                       "outcome": "fixed", "reason": "", "evidence": ""}],
            "errors": {}}


def _without_seconds(run):
    return [{k: v for k, v in d.items() if k != "seconds"} for d in run["documents"]]


def test_concurrent_documents_match_one_at_a_time_in_target_order(monkeypatch, tmp_path):
    monkeypatch.setattr(rewrite_eval, "worst_case", lambda *a: 0.01)
    _, serial = _stub_run(monkeypatch, tmp_path, "--docs", DOCS, "--budget", "5",
                          "--jobs", "1", evaluate=_staggered)
    _, concurrent = _stub_run(monkeypatch, tmp_path, "--docs", DOCS, "--budget", "5",
                              "--jobs", "5", evaluate=_staggered)
    assert [d["name"] for d in concurrent["documents"]] == DOCS.split(",")
    assert _without_seconds(concurrent) == _without_seconds(serial)


def test_no_document_starts_that_could_take_spend_past_the_budget(capsys):
    """Replays the start and finish order: at every start, what finished documents were
    charged plus every running worst case, the new one's included, is within the cap."""
    targets = [(name, "p") for name in DOCS.split(",")]
    worst, cap = {name: 1.0 for name, _ in targets}, 2.5
    events, lock = [], threading.Lock()

    def run_one(i, name, path):
        with lock:
            events.append(("start", name, 0))
        time.sleep(0.001 * (i % 3))
        charged = 1.0 if name == "strong" else 0.4  # strong had errors: charged its worst
        with lock:
            events.append(("finish", name, charged))
        return {"name": name, "charged": charged, "seconds": {"total": 0}}

    documents, skipped = harness.run_documents(targets, worst, cap, 5, run_one, lambda d: None)
    charged, running = 0.0, set()
    for kind, name, cost in events:
        if kind == "start":
            running.add(name)
            assert charged + len(running) * 1.0 <= cap, events
        else:
            running.discard(name)
            charged += cost
    assert charged <= cap and [d["name"] for d in documents] + skipped == DOCS.split(",")
    assert skipped, "the cap should have stopped the run"


def test_a_429_in_one_document_lands_in_its_errors_and_the_others_run(monkeypatch, tmp_path):
    from ats.llm import LLMError

    def evaluate(name, *a):
        if name == "slop":
            raise LLMError("openai:m: Error code: 429 - rate limited")
        return _staggered(name)

    monkeypatch.setattr(rewrite_eval, "worst_case", lambda *a: 0.01)
    _, run = _stub_run(monkeypatch, tmp_path, "--docs", DOCS, "--budget", "5",
                       evaluate=evaluate)
    by_name = {d["name"]: d for d in run["documents"]}
    assert len(by_name) == 5 and "429" in by_name["slop"]["errors"]["document"][0]
    assert by_name["slop"]["charged"] == 0.01
    assert not by_name["strong"]["errors"]


def test_each_document_records_its_step_and_total_seconds(monkeypatch, tmp_path, capsys):
    from types import SimpleNamespace as NS

    clock = iter([100.0, 107.5])
    monkeypatch.setattr(harness, "time", NS(monotonic=lambda: next(clock)))
    monkeypatch.setattr(rewrite_eval, "worst_case", lambda *a: 0.01)

    def evaluate(name, *a):
        _record((10, 0, 5, 3), seconds=2.25)
        return {"name": name, "targets": [], "errors": {},
                "seconds": {"before": 3.0, "rewrite": 2.0, "generate": 1.5}}

    _, run = _stub_run(monkeypatch, tmp_path, "--docs", "strong", "--budget", "5",
                       evaluate=evaluate)
    seconds = run["documents"][0]["seconds"]
    assert seconds == {"before": 3.0, "rewrite": 2.0, "generate": 1.5, "total": 7.5,
                       "slowest_call": 2.25}
    out = capsys.readouterr().out
    assert "(3 reasoning, 2 visible)" in out
    assert "total" in out and "7.5" in out and "slowest_call" in out


def test_a_pass_records_its_seconds(monkeypatch):
    from types import SimpleNamespace as NS

    clock = iter([0.0, 4.0])
    monkeypatch.setattr(passes, "time", NS(monotonic=lambda: next(clock)))
    result = passes.timed(lambda: PassResult())()
    assert result.meta["seconds"] == 4.0
