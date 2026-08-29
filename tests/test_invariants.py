"""The four bullet invariants, and the portability test."""
import pytest

from ats.invariants import evaluate, has_metric, portability, vacuous_number

STRONG = "Cut p99 latency 380ms to 95ms by moving Llama-3-8B to vLLM with continuous batching."
WEAK = "Responsible for utilizing various frameworks to facilitate data-driven insights."


def test_strong_bullet_satisfies_all_four():
    assert evaluate(STRONG).failures == []


def test_weak_bullet_fails_several():
    assert len(evaluate(WEAK).failures) >= 3


@pytest.mark.parametrize("text,expected", [
    ("cut latency from 380ms to 95ms", True),
    ("raised accuracy from 71% to 88%", True),
    ("served 40k tickets/month", True),
    ("collaborated with 3 engineers", False),
    ("used 5 different tools", False),
    ("improved the system", False),
])
def test_metric_detection(text, expected):
    assert has_metric(text) is expected


def test_vacuous_number_named():
    """Counting colleagues satisfies a naive quantification check while saying nothing."""
    assert vacuous_number("Collaborated with 4 engineers on 2 teams") == "4 engineers"
    assert vacuous_number("Cut latency 380ms to 95ms") is None


def test_portability_separates_generic_from_specific():
    assert portability(WEAK) > portability(STRONG)


def test_ownership_flags_team_subject():
    assert evaluate("We shipped the ranking model to production.").ownership is False
    assert evaluate("Shipped the ranking model to production.").ownership is True
