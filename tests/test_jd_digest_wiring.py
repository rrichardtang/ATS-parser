"""The digest's only path into scoring: config.dimension_multiplier(), applied in
score.py::_cost() before the anti-hard-gate ceiling. With no digest, every one of
these must reproduce today's behaviour exactly -- that's the no-op guarantee a
brand-new, empty personal corpus depends on.
"""
from ats import config
from ats.models import Category, Finding, Provenance, Severity
from ats.score import build


def _finding(rule_id, category=Category.IMPACT, severity=Severity.MAJOR):
    return Finding(
        rule_id=rule_id, category=category, severity=severity,
        message="m", fix="f", evidence="e", locator="l",
        provenance=Provenance.RECRUITER_EVIDENCE,
    )


def test_no_digest_means_multiplier_is_always_one(monkeypatch):
    monkeypatch.setattr(config, "jd_digest", lambda: {})
    assert config.dimension_multiplier("content/ownership") == 1.0


def test_digest_amplifies_a_mapped_rule_but_never_below_baseline(monkeypatch):
    monkeypatch.setattr(config, "jd_digest", lambda: {
        "dimensions": {"ownership": {"count": 5, "total": 5}}
    })
    assert config.dimension_multiplier("content/ownership") == config.DIMENSION_MAX_MULTIPLIER
    # Unmapped rule, or a dimension the corpus never mentions -- stays at baseline.
    assert config.dimension_multiplier("content/weak-opener") == 1.0
    monkeypatch.setattr(config, "jd_digest", lambda: {
        "dimensions": {"ownership": {"count": 0, "total": 5}}
    })
    assert config.dimension_multiplier("content/ownership") == 1.0


def test_amplification_actually_moves_an_unclamped_finding(monkeypatch):
    """Below the ceiling, amplifying a rule the user's target roles emphasize
    should cost more than the same finding does by default."""
    baseline = build([_finding("content/ownership", Category.IMPACT, Severity.MINOR)])
    monkeypatch.setattr(config, "jd_digest", lambda: {
        "dimensions": {"ownership": {"count": 5, "total": 5}}
    })
    amplified = build([_finding("content/ownership", Category.IMPACT, Severity.MINOR)])
    assert amplified.composite < baseline.composite


def test_amplified_rule_still_respects_the_anti_hard_gate_ceiling(monkeypatch):
    """Even fully amplified (5/5), a rule still can't move the composite by more
    than its category's weight -- amplification happens before the ceiling clamp,
    not instead of it."""
    weights = config.category_weights()
    monkeypatch.setattr(config, "jd_digest", lambda: {
        "dimensions": {"ownership": {"count": 5, "total": 5}}
    })
    amplified = build([_finding("content/ownership", Category.IMPACT, Severity.CRITICAL)])
    lost = 100.0 - amplified.composite
    assert lost <= weights[Category.IMPACT] + 0.01
