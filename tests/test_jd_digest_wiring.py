"""The digest's only path into scoring: config.dimension_multiplier(), applied in
score.py::_cost() before the anti-hard-gate ceiling. With no digest, every one of
these must reproduce today's behaviour exactly -- that's the no-op guarantee a
brand-new, empty personal corpus depends on.

Ticket 09 left `title/seniority-mismatch` as the only mapped rule, so it is what these
exercise. The four rules dropped alongside it (content/ownership, cred/no-production,
cred/notebook-only, cred/no-evaluation) have their own test below: a rule whose
category now derives its weight from the same document frequency must not also have
its cost scaled by it.
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
    assert config.dimension_multiplier("title/seniority-mismatch") == 1.0


def test_digest_amplifies_a_mapped_rule_but_never_below_baseline(monkeypatch):
    monkeypatch.setattr(config, "jd_digest", lambda: {
        "dimensions": {"seniority": {"count": 5, "total": 5}}
    })
    assert config.dimension_multiplier("title/seniority-mismatch") == config.DIMENSION_MAX_MULTIPLIER
    # Unmapped rule, or a dimension the corpus never mentions -- stays at baseline.
    assert config.dimension_multiplier("content/weak-opener") == 1.0
    monkeypatch.setattr(config, "jd_digest", lambda: {
        "dimensions": {"seniority": {"count": 0, "total": 5}}
    })
    assert config.dimension_multiplier("title/seniority-mismatch") == 1.0


def test_a_rule_whose_category_derives_its_weight_is_never_also_scaled(monkeypatch):
    """Ticket 04's double count, asserted rather than remembered. Every behaviour
    dimension sets a category weight now, so no rule may read one as a multiplier."""
    monkeypatch.setattr(config, "jd_digest", lambda: {
        "dimensions": {
            name: {"count": 6, "total": 6}
            for name in ("ownership", "production", "evaluation", "reliability",
                         "agentic", "ai_assisted_coding")
        }
    })
    for rule_id in ("content/ownership", "cred/no-production", "cred/notebook-only",
                    "cred/no-evaluation"):
        assert config.dimension_multiplier(rule_id) == 1.0


def test_amplification_actually_moves_an_unclamped_finding(monkeypatch):
    """Below the ceiling, amplifying a rule the user's target roles emphasize
    should cost more than the same finding does by default.

    Asserted on the category rather than the composite: 09 left one mapped rule, and
    its category is weighted 5 of 100, so the largest composite movement the whole
    mechanism can now produce is 0.05 points -- below the report's own rounding. That
    is a fact about what `dimension_multiplier()` is still worth, recorded in
    docs/wayfinder/rubric-grounding/dimension-scan.md.
    """
    def title_score(report):
        return next(c.score for c in report.categories if c.category == Category.TITLE)

    monkeypatch.setattr(config, "jd_digest", lambda: {
        "dimensions": {"seniority": {"count": 0, "total": 5}}
    })
    baseline = build([_finding("title/seniority-mismatch", Category.TITLE, Severity.MINOR)])
    monkeypatch.setattr(config, "jd_digest", lambda: {
        "dimensions": {"seniority": {"count": 5, "total": 5}}
    })
    amplified = build([_finding("title/seniority-mismatch", Category.TITLE, Severity.MINOR)])
    assert title_score(amplified) < title_score(baseline)


def test_amplified_rule_still_respects_the_anti_hard_gate_ceiling(monkeypatch):
    """Even fully amplified (5/5), a rule still can't move the composite by more
    than its category's weight -- amplification happens before the ceiling clamp,
    not instead of it."""
    weights = config.category_weights()
    monkeypatch.setattr(config, "jd_digest", lambda: {
        "dimensions": {"seniority": {"count": 5, "total": 5}}
    })
    amplified = build([_finding("title/seniority-mismatch", Category.TITLE, Severity.CRITICAL)])
    lost = 100.0 - amplified.composite
    assert lost <= weights[Category.TITLE] + 0.01
