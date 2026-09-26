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
