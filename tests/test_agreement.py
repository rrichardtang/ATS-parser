"""The agreement harness, against stubbed judges. No network.

What matters here is that the harness can tell apart the three things the
acceptance test conflates if you only look at one number: two judges genuinely
disagreeing, one judge disagreeing with itself, and two judges agreeing because
every resume lands in the same place anyway.
"""
import json

import pytest

from ats import agreement, llm, passes, prompts
from ats import pipeline
from ats.agreement_table import render
from ats.extract import extract
from ats.sections import parse
from ats.llm import Provider
from ats.models import Category

# The five categories the content prompt actually asks the model to score.
CATEGORIES = prompts.CATEGORY_NAMES


def _reply(scores, unmet_criteria=()):
    """A content reply carrying both channels.

    The `score` per category is what a run recorded before ticket 05 carries, and the
    numeric agreement tables are still measured on runs like it. `criteria` is what a
    judge answers now: each entry here is a criterion answered `no` with a quote and a
    place, which is what `passes.place` turns into a placed finding.
    """
    return json.dumps({
        "categories": {
            name: {
                "score": value,
                "why": "because",
                "criteria": [
                    {"id": cid, "answer": "no", "why": why, "fix": "do it",
                     "evidence": evidence, "locator": locator}
                    for cid, why, evidence, locator in (
                        unmet_criteria if name == Category.PRODUCTION_OWNERSHIP.value
                        else ()
                    )
                ],
            }
            for name, value in scores.items()
        },
    })


def _judges(monkeypatch, table):
    """table: {provider: [reply per sample]}. Each call takes the next sample."""
    used = {name: 0 for name in table}

    def dispatch(provider, system, user, temperature):
        if "detect AI-generated writing" in system:
            return json.dumps({"findings": []})
        replies = table[provider.name]
        reply = replies[used[provider.name] % len(replies)]
        used[provider.name] += 1
        return reply

    monkeypatch.setattr(llm, "_dispatch", dispatch)
    return [Provider("anthropic", "k", "claude-x"), Provider("openai", "k", "gpt-x")]


AGREEING = _reply(dict.fromkeys(CATEGORIES, 60))
DISAGREEING = _reply(dict.fromkeys(CATEGORIES, 82))


def test_between_and_within_spread_are_reported_separately(monkeypatch, fixtures):
    """A provider that wobbles by 4 and differs from its peer by 22 must show both.

    Folding either into the other is what makes the acceptance test unmeasurable:
    a 22-point gap means nothing if the same judge moves 20 on a rerun.
    """
    providers = _judges(monkeypatch, {
        "anthropic": [_reply(dict.fromkeys(CATEGORIES, 60)),
                      _reply(dict.fromkeys(CATEGORIES, 64))],
        "openai": [_reply(dict.fromkeys(CATEGORIES, 84)),
                   _reply(dict.fromkeys(CATEGORIES, 84))],
    })
    run = agreement.collect(providers, [("strong", str(fixtures["strong"]))], 2, 0.7)
    report = agreement.analyse(run)

    assert report.numeric, "no category was measured"
    row = report.numeric[0]
    assert row.between_mean == pytest.approx(22.0, abs=0.1)
    assert row.within_mean == pytest.approx(2.0, abs=0.1)  # 4 for one provider, 0 for the other
    assert row.within_max == pytest.approx(4.0, abs=0.1)


def test_a_resume_with_no_text_layer_is_skipped_not_crashed(monkeypatch, fixtures):
    providers = _judges(monkeypatch, {"anthropic": [AGREEING], "openai": [AGREEING]})
    run = agreement.collect(providers, [("scanned", str(fixtures["scanned"]))], 2, 0.7)
    assert run.resumes[0].skipped
    assert not run.resumes[0].judgments
    report = agreement.analyse(run)
    assert report.skipped == [("scanned", run.resumes[0].skipped)]


def test_one_provider_says_so_rather_than_reporting_agreement(monkeypatch, fixtures):
    providers = [_judges(monkeypatch, {"anthropic": [AGREEING]})[0]]
    run = agreement.collect(providers, [("strong", str(fixtures["strong"]))], 2, 0.7)
    report = agreement.analyse(run)
    assert any("cannot be measured with one judge" in n for n in report.notes)

    category = report.numeric[0].category
    line = next(l for l in render(report).splitlines() if l.startswith(category))
    _n, between, between_max, *_ = line[len(category):].split()
    assert (between, between_max) == ("-", "-"), \
        "a lone judge must print no between-judge spread, not a zero that reads as one"


def test_the_composite_bar_separates_pass_look_and_fail():
    assert agreement.verdict(4.9) == agreement.PASS
    assert agreement.verdict(5.0) == agreement.PASS
    assert agreement.verdict(6.0) == agreement.LOOK
    assert agreement.verdict(8.1) == agreement.FAIL


def test_model_findings_deduct_today_and_not_under_ticket_03(monkeypatch, fixtures):
    """The double count 03 closed, measured rather than argued.

    One judge writes four findings and the other writes none, on identical
    category numbers. Today that difference alone moves the composite; under 03's
    decision -- findings are evidence for the band, not a deduction -- it cannot.
    """
    wordy = _reply(dict.fromkeys(CATEGORIES, 60), [
        (f"C{i + 1}", f"bullet {i} states no outcome", "Cut p99 inference latency",
         f"exp[0].bullet[{i}]")
        for i in range(4)
    ])
    providers = _judges(monkeypatch, {"anthropic": [wordy], "openai": [AGREEING]})
    run = agreement.collect(providers, [("strong", str(fixtures["strong"]))], 1, 0.0)
    report = agreement.analyse(run)

    row = report.composites[0]
    assert row.spread_as_built > 0, "findings should move today's composite"
    assert row.spread_no_deduct == pytest.approx(0.0, abs=0.05)


def test_findings_agreement_keys_on_defect_kind_and_place_not_wording(monkeypatch, fixtures):
    """Two judges naming the same defect in the same place have agreed."""
    same_defect = "exp[0].bullet[0]"
    a = _reply(dict.fromkeys(CATEGORIES, 60),
               [("C3", "no scale given here", "Cut p99 inference latency", same_defect)])
    b = _reply(dict.fromkeys(CATEGORIES, 60),
               [("C3", "this bullet never says how big", "Cut p99 inference latency", same_defect)])
    providers = _judges(monkeypatch, {"anthropic": [a], "openai": [b]})
    run = agreement.collect(providers, [("strong", str(fixtures["strong"]))], 1, 0.0)
    report = agreement.analyse(run)
    keyed = {row.key: row for row in report.findings if row.resume == "strong"}
    assert keyed["kind+locator"].between == 1.0
    # Same place, same kind, different wording: only the evidence key sees a
    # disagreement, and it is the wording one -- which is why it is not the key
    # of record (ticket 10).
    assert keyed["locator"].between == 1.0
    assert keyed["evidence"].between == 1.0


def test_findings_agreement_reports_a_chance_line_under_every_key(monkeypatch, fixtures):
    """Ticket 10: raw overlap cannot tell agreement from a short shared list.

    Both judges flag both of the same two places, so raw overlap is a perfect
    1.00 -- and chance is 1.00 too, because there were only ever two keys in
    play and each judge took both. Kappa is what says so.
    """
    places = [("C3", "no scale", "Cut p99 inference latency", "exp[0].bullet[0]"),
              ("C3", "no scale", "Cut p99 inference latency", "exp[0].bullet[1]")]
    providers = _judges(monkeypatch, {
        "anthropic": [_reply(dict.fromkeys(CATEGORIES, 60), places)],
        "openai": [_reply(dict.fromkeys(CATEGORIES, 60), places)],
    })
    run = agreement.collect(providers, [("strong", str(fixtures["strong"]))], 1, 0.0)
    report = agreement.analyse(run)
    row = next(r for r in report.findings if r.key == "locator")
    assert row.between == 1.0
    assert row.chance == 1.0
    assert row.kappa is None, "no headroom over chance means kappa is undefined, not 1.0"


def test_bands_are_read_when_the_reply_carries_them():
    """Ticket 05 has not landed bands; this is the path waiting for them."""
    def banded(band):
        return passes.ContentJudgment(
            provider="anthropic" if band == "thin" else "openai",
            sample=0,
            categories={Category.PRODUCTION_OWNERSHIP.value: {"band": band}},
            findings=[],
        )

    run = agreement.HarnessRun(
        meta={"providers": ["a", "b"]},
        resumes=[agreement.ResumeRun("strong", "x", [], [banded("thin"), banded("solid")])],
    )
    report = agreement.analyse(run, band_order=["absent", "thin", "solid", "strong"])
    assert report.bands[0].adjacent == 1
    assert report.bands[0].verdict == agreement.LOOK
    assert not report.numeric, "a band carries no number to spread"


def test_a_judge_that_names_two_bands_for_one_resume_is_unstable_not_averaged():
    wobbly = [
        passes.ContentJudgment("anthropic", 0, {Category.PRODUCTION_OWNERSHIP.value: {"band": "thin"}}, []),
        passes.ContentJudgment("anthropic", 1, {Category.PRODUCTION_OWNERSHIP.value: {"band": "strong"}}, []),
        passes.ContentJudgment("openai", 0, {Category.PRODUCTION_OWNERSHIP.value: {"band": "thin"}}, []),
        passes.ContentJudgment("openai", 1, {Category.PRODUCTION_OWNERSHIP.value: {"band": "thin"}}, []),
    ]
    run = agreement.HarnessRun(resumes=[agreement.ResumeRun("strong", "x", [], wobbly)])
    report = agreement.analyse(run, band_order=["absent", "thin", "solid", "strong"])
    assert report.bands[0].unstable == 1
    assert report.bands[0].exact == 0


def test_a_saved_run_round_trips_so_a_rerender_needs_no_calls(monkeypatch, fixtures):
    providers = _judges(monkeypatch, {"anthropic": [AGREEING], "openai": [DISAGREEING]})
    run = agreement.collect(providers, [("strong", str(fixtures["strong"]))], 2, 0.7)
    restored = agreement.HarnessRun.from_dict(json.loads(json.dumps(run.to_dict())))
    assert render(agreement.analyse(restored)) == render(
        agreement.analyse(run)
    )


def test_the_table_renders_every_section(monkeypatch, fixtures):
    providers = _judges(monkeypatch, {"anthropic": [AGREEING], "openai": [DISAGREEING]})
    run = agreement.collect(
        providers,
        [("strong", str(fixtures["strong"])), ("scanned", str(fixtures["scanned"]))],
        2, 0.7, notes=["a note"],
    )
    text = render(agreement.analyse(run))
    for expected in ("Per-category agreement", "Composite spread between judges",
                     "Findings agreement", "Skipped", "Notes", Category.PRODUCTION_OWNERSHIP.value):
        assert expected in text, f"missing {expected!r}"


def test_a_capped_composite_is_marked_rather_than_counted_as_agreement(fixtures):
    """A composite pinned by the fraud cap has a spread of 0 whatever the judges said.

    A bare pass on that row would be the same coincidence the chance correction
    exists to catch one level up. The run is built here rather than collected: since
    05 the `hidden_text` fixture parses to no roles at all, so the harness withholds
    it before a judge is asked -- which is the test below this one.
    """
    doc = extract(str(fixtures["hidden_text"]))
    resume = parse(doc.text)
    deterministic = pipeline.deterministic(
        doc, resume, "", pipeline.resolve_target_title("")
    )
    assert any(f.rule_id == "parse/hidden-text" for f in deterministic)

    run = agreement.HarnessRun(
        meta={"providers": ["anthropic", "openai"]},
        resumes=[agreement.ResumeRun("hidden_text", "x", deterministic, [
            _numeric("anthropic", 0, dict.fromkeys(CATEGORIES, 60)),
            _numeric("openai", 0, dict.fromkeys(CATEGORIES, 82)),
        ])],
    )
    report = agreement.analyse(run)

    assert report.composites[0].capped
    assert report.composites[0].spread_as_built == 0.0
    text = render(report)
    assert "hidden_text *" in text
    assert "pinned by a cap" in text


def test_a_document_whose_roles_did_not_parse_is_withheld_not_judged(monkeypatch, fixtures):
    """05's withholding rule, at the harness.

    `two_column` has a text layer, so the no-text-layer skip does not catch it -- and
    it parses to zero roles, so every criterion would be answered about bullets that
    are not there. Judging it anyway would put agreement numbers in the table for the
    one kind of document the pipeline refuses to judge.
    """
    providers = _judges(monkeypatch, {"anthropic": [AGREEING], "openai": [AGREEING]})
    run = agreement.collect(providers, [("two_column", str(fixtures["two_column"]))], 2, 0.7)

    assert "withheld" in run.resumes[0].skipped
    assert not run.resumes[0].judgments
    assert agreement.analyse(run).skipped == [("two_column", run.resumes[0].skipped)]


def test_a_lone_judge_never_counts_as_band_agreement():
    """One judge's band matches itself by construction; that is not evidence."""
    alone = [passes.ContentJudgment("anthropic", i, {Category.PRODUCTION_OWNERSHIP.value: {"band": "thin"}}, [])
             for i in range(2)]
    run = agreement.HarnessRun(resumes=[agreement.ResumeRun("strong", "x", [], alone)])
    report = agreement.analyse(run, band_order=["absent", "thin", "solid", "strong"])
    assert report.bands[0].resumes == 0
    assert report.bands[0].exact == 0


def test_an_unstable_judge_costs_the_category_its_verdict():
    """A rubric no judge can apply twice running has not passed anything."""
    wobbly = [
        passes.ContentJudgment("anthropic", 0, {Category.PRODUCTION_OWNERSHIP.value: {"band": "thin"}}, []),
        passes.ContentJudgment("anthropic", 1, {Category.PRODUCTION_OWNERSHIP.value: {"band": "strong"}}, []),
        passes.ContentJudgment("openai", 0, {Category.PRODUCTION_OWNERSHIP.value: {"band": "thin"}}, []),
        passes.ContentJudgment("openai", 1, {Category.PRODUCTION_OWNERSHIP.value: {"band": "thin"}}, []),
    ]
    run = agreement.HarnessRun(resumes=[agreement.ResumeRun("strong", "x", [], wobbly)])
    row = agreement.analyse(run, band_order=["absent", "thin", "solid", "strong"]).bands[0]
    assert (row.unstable, row.exact) == (1, 0)
    assert row.verdict == agreement.LOOK


def _numeric(provider, sample, scores):
    return passes.ContentJudgment(provider, sample, {k: {"score": v} for k, v in scores.items()}, [])


def test_a_category_only_one_judge_scored_reports_no_between_spread():
    """Two providers ran; only one answered on this category. That is not agreement.

    The guard has to be per category, not per run: with both providers present a
    run-level check passes and the row prints 0.0 beside an alpha of n/a, two
    numbers on one line contradicting each other.
    """
    both = Category.PRODUCTION_OWNERSHIP.value
    lone = Category.RESUME_CRAFT.value
    run = agreement.HarnessRun(resumes=[agreement.ResumeRun("strong", "x", [], [
        _numeric("anthropic", 0, {both: 70, lone: 55}),
        _numeric("openai", 0, {both: 64}),
    ])])
    rows = {row.category: row for row in agreement.analyse(run).numeric}

    assert rows[both].between_mean == pytest.approx(6.0)
    assert rows[lone].between_mean is None
    assert rows[lone].over_bar == 0, "a judge with no number is not a judge to compare against"

    line = next(l for l in render(agreement.analyse(run)).splitlines() if l.startswith(lone))
    assert line[len(lone):].split()[1] == "-"


def test_one_sample_reports_no_within_judge_noise_floor():
    """With nothing to rerun against, the floor is unmeasured, not zero."""
    run = agreement.HarnessRun(resumes=[agreement.ResumeRun("strong", "x", [], [
        _numeric("anthropic", 0, {Category.PRODUCTION_OWNERSHIP.value: 70}),
        _numeric("openai", 0, {Category.PRODUCTION_OWNERSHIP.value: 64}),
    ])])
    row = agreement.analyse(run).numeric[0]
    assert row.within_mean is None and row.within_max is None


def test_a_resume_only_one_judge_scored_gets_no_composite_verdict(monkeypatch, fixtures):
    """One provider erroring must not turn into a composite spread of 0.0 -> pass."""
    def half_dead(provider, system, user, temperature):
        if "detect AI-generated writing" in system:
            return json.dumps({"findings": []})
        if provider.name == "openai":
            raise llm.LLMError("openai:gpt-x: 429 rate limited")
        return AGREEING

    monkeypatch.setattr(llm, "_dispatch", half_dead)
    providers = [Provider("anthropic", "k", "claude-x"), Provider("openai", "k", "gpt-x")]
    run = agreement.collect(providers, [("strong", str(fixtures["strong"]))], 2, 0.7)
    report = agreement.analyse(run)

    assert not report.composites[0].comparable
    text = render(report)

    section = text.split("Composite spread")[1].split("Composite by judge")[0]
    row = next(l for l in section.splitlines() if l.startswith("strong"))
    assert row.split()[1:] == ["-", "-", "-", "-"], f"verdict printed on one judge: {row!r}"
    assert "1 pass" not in section and "1 look" not in section and "1 FAIL" not in section
    assert any("429 rate limited" in note for note in report.notes), \
        "a sweep that lost calls must say so beside its numbers"
    assert "judged by   anthropic" in text


def test_a_recording_that_carries_both_shapes_keeps_its_numbers():
    """A judgement can hold criteria for one category and a pre-05 `score` for another.

    The numeric fallback fills per *category*, not per judgement: an all-or-nothing
    fallback drops every recorded number the moment one category bands, which inflates
    the before picture the fallback exists to preserve. `Resume craft` read 100 -- its
    rule channel alone -- instead of the 82 its recorded 40 buys.
    """
    from ats.agreement import ResumeRun, score_judgment

    criteria = [{"id": f"C{i}", "answer": "no", "why": "x", "evidence": "", "locator": ""}
                for i in range(1, 6)]

    def scored(categories):
        judgment = passes.ContentJudgment(
            provider="anthropic", sample=0, categories=categories, findings=[])
        return score_judgment(
            ResumeRun(name="r", path="r", judgments=[judgment]), judgment)

    mixed = scored({"Production ownership": {"criteria": criteria},
                    "Resume craft": {"score": 40}})
    pure = scored({"Resume craft": {"score": 40}})

    assert mixed.categories["Resume craft"] == pure.categories["Resume craft"] == 82.0
    # and the criteria half still bands rather than falling back
    assert mixed.categories["Production ownership"] == 46.0
