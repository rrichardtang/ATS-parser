"""The harness's own flags, with no provider and no network."""
from argparse import Namespace

import pytest

from ats import agreement
from ats.agreement_table import render
from scripts import agreement_harness as harness


def _args(**overrides):
    return Namespace(**{"docs": "", "only": "", "acceptance_set": False, "resume": None,
                        **overrides})


def test_docs_picks_named_targets_across_fixtures_and_the_acceptance_set():
    accepted = harness.acceptance_targets()[0][0]
    targets, notes = harness.select_targets(_args(docs=f"strong,{accepted}"))

    assert [name for name, _ in targets] == ["strong", accepted]
    assert any("of the 7 fixtures" in note for note in notes)
    assert any("acceptance-set documents were run" in note for note in notes)


def test_docs_refuses_an_unknown_name():
    with pytest.raises(SystemExit, match="unknown document.*nope"):
        harness.select_targets(_args(docs="strong,nope"))


@pytest.mark.parametrize("flags", [
    ["--max-tokens", "-10000000"], ["--max-tokens", "0"], ["--samples", "0"],
    ["--openai-price", "-1,-1"], ["--openai-price", "1,-8"],
])
def test_out_of_range_values_are_rejected_by_the_parser(monkeypatch, flags):
    monkeypatch.setattr("sys.argv", ["agreement_harness", "--dry-run", *flags])
    with pytest.raises(SystemExit) as stopped:
        harness.main()
    assert stopped.value.code == 2


def _plan_args(**overrides):
    return Namespace(**{"claude_only": False, "no_claude": False, "max_tokens": 25000,
                        "openai_max_tokens": 16000, "openai_effort": "medium",
                        "samples": 2, "votes": 3, "claude_samples": 1, **overrides})


def test_openai_effort_and_cap_reach_the_provider_the_meta_and_the_sampling_line():
    [luna] = harness.chosen_providers(
        _plan_args(no_claude=True, openai_max_tokens=24000, openai_effort="high"),
        {"openai": "-"})
    assert (luna.openai_max_tokens, luna.openai_effort) == (24000, "high")
    meta = agreement.run_meta([luna], {"openai": (2, 3)}, 0.7)
    assert meta["openai_effort"] == "high"
    assert "OpenAI effort high" in render(agreement.AgreementReport(meta=meta, providers=[luna.label]))


def test_the_default_plan_votes_openai_and_asks_claude_once():
    args = _plan_args()
    providers = harness.chosen_providers(args, {"anthropic": "-", "openai": "-"})
    assert harness.run_plan(args, providers) == {"anthropic": (1, 1), "openai": (2, 3)}
    assert all(p.openai_max_retries == 0 for p in providers)


@pytest.mark.parametrize("flag, left", [("claude_only", "anthropic"), ("no_claude", "openai")])
def test_one_judge_flags_leave_the_other_out(flag, left):
    providers = harness.chosen_providers(_plan_args(**{flag: True}),
                                         {"anthropic": "-", "openai": "-"})
    assert [p.name for p in providers] == [left]
