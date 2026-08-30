"""The baseline decomposition (scripts/baseline_analysis.py).

Two things need pinning. The redaction must actually redact -- the extract is
committed, and it is derived from a file that quotes resumes verbatim. And the
decomposition must keep separating what it separated on the first real run: a
directional offset, the residual left after removing it, and the fact that the
findings key decides the answer.
"""
import json
from pathlib import Path

import pytest

from scripts.baseline_analysis import (
    direction,
    extract,
    key_table,
    load,
    offset_table,
    report,
    vocabulary,
)

SUMMARY = (Path(__file__).resolve().parents[1] / "docs" / "wayfinder" /
           "rubric-grounding" / "baseline" / "run-summary.json")


@pytest.fixture(scope="module")
def run():
    return load(SUMMARY)


def _raw_shaped(judgments):
    """A run in the raw harness shape, with the text fields the extract must drop."""
    return {
        "meta": {"providers": ["anthropic:m", "openai:m"], "samples_per_provider": 2},
        "resumes": [{
            "name": "Someone_Real_Resume", "path": "/home/someone/cv.pdf",
            "skipped": False, "errors": [], "deterministic": [],
            "judgments": judgments,
        }],
    }


def test_extract_drops_every_field_that_quotes_a_resume():
    raw = _raw_shaped([{
        "provider": "anthropic:m", "sample": 0,
        "categories": {"Impact": {"score": 60, "why": "SECRET the bullets in the first role are strong"}},
        "findings": [{"rule_id": "llm/missing-scale", "locator": "exp[0].bullet[1]",
                      "severity": "major", "source": "llm:anthropic",
                      "evidence": "SECRET verbatim line from the resume",
                      "message": "SECRET paraphrase", "fix": "SECRET suggestion"}],
    }])
    blob = json.dumps(extract(raw))
    assert "SECRET" not in blob
    assert "/home/someone" not in blob
    assert "Someone_Real_Resume" not in blob
    # What survives is the arithmetic: scores, rule ids, locators.
    assert "llm/missing-scale" in blob and "exp[0].bullet[1]" in blob and "60" in blob


def test_extract_keeps_repo_fixtures_under_their_own_names():
    raw = _raw_shaped([])
    raw["resumes"][0]["name"] = "two_column"
    assert extract(raw)["resumes"][0]["name"] == "two_column"


def test_the_committed_extract_carries_no_free_text():
    payload = json.loads(SUMMARY.read_text(encoding="utf-8"))
    for resume in payload["resumes"]:
        assert not resume["name"].lower().startswith("tang")
        for judgment in resume["judgments"]:
            for entry in judgment["categories"].values():
                assert set(entry) == {"score"}
            for finding in judgment["findings"]:
                assert set(finding) <= {"rule_id", "locator", "severity", "source"}


def test_the_disagreement_is_directional(run):
    """The finding the whole decomposition exists to state."""
    low, high, positive, total, mean = direction(run)
    assert (low, high) == ("anthropic", "openai")
    assert positive / total > 0.9, "offset is no longer near-total; re-read the doc"
    assert mean > 10


def test_removing_the_offset_does_not_rescue_the_categories(run):
    """The correction to the first reading: the offset is about half the problem."""
    rows = offset_table(run)
    assert len(rows) == 5
    for _, _, _, residual_mean, _, within_five, n in rows:
        assert residual_mean > 5, "residual now passes the bar; the doc needs updating"
        assert within_five < n


def test_judges_rank_alike_even_where_they_score_apart(run):
    """Rank agreement is what makes the offset a calibration story rather than chaos."""
    for category, _, _, _, rho, _, _ in offset_table(run):
        assert rho is not None and rho > 0.7, category


def test_the_key_decides_the_answer(run):
    """Keying on a model-invented name reads as disagreement that locators deny."""
    rows = {key: (within, between) for key, within, between in
            key_table(run, ("rule+locator", "locator"))}
    assert rows["rule+locator"][1] < 0.1
    assert rows["locator"][1] > 0.4
    # Within-judge barely beats between-judge: the instability is sampling, not provider.
    assert abs(rows["locator"][0] - rows["locator"][1]) < 0.15


def test_the_judges_invent_a_name_per_finding(run):
    overall, per_provider = vocabulary(run)
    assert len(overall) > 100
    left, right = (set(c) for c in per_provider.values())
    assert len(left & right) <= 10


def test_report_renders_from_the_redacted_extract(run):
    text = report(run)
    assert "Baseline decomposition" in text
    assert "redacted extract" in text
