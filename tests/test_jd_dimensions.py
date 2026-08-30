"""Dimension detection: phrases that describe scope/seniority/ownership rather
than naming a skill, so they can't be taxonomy terms.
"""
from ats.jd_dimensions import scan


def test_ownership_phrase_without_the_word_ownership():
    hits = scan("You'll own production systems end to end.")
    assert "ownership" in hits


def test_production_and_evaluation_and_seniority_and_leadership():
    text = (
        "You'll carry on-call for the service and set the SLA. "
        "We run rigorous evals before every launch. "
        "Comfortable with ambiguous problems and minimal oversight. "
        "You'll mentor other engineers on the team."
    )
    hits = scan(text)
    assert {"production", "evaluation", "seniority", "leadership"} <= hits


def test_plain_bullet_hits_nothing():
    assert scan("Built a REST API in Flask.") == set()
