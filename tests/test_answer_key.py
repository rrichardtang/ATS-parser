"""The owner's answer key (ticket 15, 28 September), and a judge scored against it."""
import json

import pytest

from ats.agreement import HarnessRun, ResumeRun
from ats.answer_key import KEY, MISSING, judge_answer, load, score
from ats.passes import ContentJudgment, criteria_index, voted_judgment
from ats.sections import parse
from scripts import agreement_harness as harness

SYNTHETIC = KEY.parent / "synthetic"
ENTRIES = load(KEY)


def _resume_text(doc):
    return (SYNTHETIC / f"{doc}.txt").read_text(encoding="utf-8")


@pytest.mark.parametrize("entry", ENTRIES, ids=lambda e: f"{e['doc'][:2]}-{e['category']}-"
                                                      f"{e['criterion']}-{e.get('locator')}")
def test_every_key_entry_names_a_real_criterion_and_quotes_the_resume(entry):
    """A scoped entry is keyed per place: its quote is the parsed text at its locator,
    so a parser change that moves a locator fails here rather than misscoring a run."""
    criteria = {slug: found for slug, found in criteria_index().values()}
    criterion = criteria[entry["category"]][entry["criterion"]]
    assert entry["answer"] in ("yes", "no")
    assert ("locator" in entry) == ("scope" in criterion)
    text = _resume_text(entry["doc"])
    if "locator" in entry:
        resume = parse(text)
        at = dict(resume.bullets, summary=resume.summary)
        assert at[entry["locator"]] == entry["quote"]
    else:
        assert entry["quote"] in " ".join(text.split())


SINGLE = {"doc": "a", "category": "agentic-systems", "criterion": "C1", "answer": "yes",
          "quote": "Shipped the agent.", "date": "2026-09-28"}
SCOPED = {"doc": "a", "category": "production-ownership", "criterion": "C4",
          "locator": "exp[0].bullet[1]", "answer": "no", "quote": "Ran a benchmark.",
          "date": "2026-09-28"}


def _judgment(provider, sample, agentic=None, places=None):
    categories = {}
    if agentic is not None:
        categories["Agentic systems"] = {"criteria": [{"id": "C1", "answer": agentic}]}
    if places is not None:
        categories["Production ownership"] = {"criteria": [
            {"id": "C4", "answer": "yes", "places": places}]}
    return ContentJudgment(provider, sample, categories, [], [])


def _run(*judgments, skipped=""):
    return HarnessRun(resumes=[ResumeRun("a", "a.pdf", judgments=list(judgments),
                                         skipped=skipped)])


def test_a_scoped_item_is_compared_at_its_place_not_on_the_derived_answer():
    places = [{"locator": "exp[0].bullet[0]", "answer": "yes"},
              {"locator": "exp[0].bullet[1]: Ran a benchmark.", "answer": "no"}]
    [result] = score(_run(_judgment("openai", 0, "yes", places)), [SINGLE, SCOPED])
    assert (result.matched, result.scored) == (2, 2)


def test_a_wrong_or_absent_answer_is_a_mismatch_and_absent_is_marked_missing():
    places = [{"locator": "exp[0].bullet[0]", "answer": "yes"}]
    [result] = score(_run(_judgment("openai", 0, "no", places)), [SINGLE, SCOPED])
    assert result.matched == 0
    assert [(e["criterion"], got) for e, got in result.mismatches] == [
        ("C1", "no"), ("C4", MISSING)]


def test_each_voted_sample_is_scored_and_a_sample_missing_from_a_resume_misses_it():
    run = _run(_judgment("openai", 0, "yes"), _judgment("openai", 1, "no"))
    run.resumes.append(ResumeRun("b", "b.pdf", judgments=[_judgment("openai", 0, "yes")]))
    other = {**SINGLE, "doc": "b"}
    scores = {s.judge: s for s in score(run, [SINGLE, other])}
    assert (scores["openai sample 0"].matched, scores["openai sample 0"].scored) == (2, 2)
    assert [got for _, got in scores["openai sample 1"].mismatches] == ["no", MISSING]


def test_every_key_entry_is_scored_and_skipped_or_absent_documents_are_missing():
    outside = {**SINGLE, "doc": "not-in-the-run"}
    [result] = score(_run(_judgment("openai", 0, "yes"), skipped="no text layer"),
                     [SINGLE, outside])
    assert result.matched == 0
    assert [got for _, got in result.mismatches] == [MISSING, MISSING]


def test_a_planned_sample_that_answered_nothing_still_gets_its_line():
    run = _run(_judgment("openai", 0, "yes"))
    run.meta = {"samples_per_provider": {"openai": 2}}
    scores = {s.judge: s for s in score(run, [SINGLE])}
    assert scores["openai sample 1"].mismatches == [(SINGLE, MISSING)]


def test_a_replayed_run_prints_each_judge_against_the_key(tmp_path, monkeypatch, capsys):
    saved, key = tmp_path / "run.json", tmp_path / "key.json"
    saved.write_text(json.dumps(_run(_judgment("openai", 0, "yes"),
                                     _judgment("openai", 1, "no")).to_dict()))
    key.write_text(json.dumps({"entries": [SINGLE]}))
    monkeypatch.setattr("sys.argv", ["agreement_harness", "--from", str(saved),
                                     "--key", str(key)])
    harness.main()
    out = capsys.readouterr().out
    assert "openai sample 0" in out and "1/1 matched" in out
    assert "a / agentic-systems/C1 / - / key yes vs judge no" in out


def test_a_voted_sample_votes_the_keyed_place_across_every_try():
    """The copied try says yes at the keyed place; two of three say no, so the vote is no."""
    resume = parse("Riley Tang\nriley@example.com\n\nEXPERIENCE\n"
                   "AI Engineer, Northwind Data    Mar 2024 - Present\n"
                   "• Shipped the fraud service.\n• Ran a benchmark.\n")
    tries = [_judgment("openai", i, places=[
        {"locator": "exp[0].bullet[0]", "answer": "yes", "evidence": "Shipped the fraud service."},
        {"locator": "exp[0].bullet[1]", "answer": keyed}]) for i, keyed in
        enumerate(["yes", "no", "no"])]
    for t in tries:
        t.categories["Production ownership"]["criteria"][0].update(
            locator="exp[0].bullet[0]", evidence="Shipped the fraud service.")
    voted = voted_judgment(tries, resume, 0)
    assert judge_answer(voted.categories, SCOPED) == "no"
