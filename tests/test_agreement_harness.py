"""The harness's own flags, with no provider and no network."""
from argparse import Namespace

import pytest

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
