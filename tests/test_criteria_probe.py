"""The criteria probe: what the measurement rests on, not what the rubric says.

The rubric's own properties -- the band lookup being total and monotone, and the two
lookup shapes -- moved to `tests/test_rubric.py` with the lookup itself. What is pinned
here is the probe: injected text must never answer a criterion, a document whose roles
did not parse must be withheld rather than answered, the deterministic judge must carry
a span for every `yes` or abstain outright, and the recorded judge verdicts must be
complete binary answers over the declared criteria.

Every property is parametrised over all five categories. A category added later gets
the whole suite by appearing in `SLUGS`, which is the point: 05 measured the format on
one category, and the properties are what has to hold for the next one.
"""
import pytest

from ats.rubric import SLUGS, band_of, load_spec
from ats.sections import parse
from scripts.criteria_probe import (
    Doc,
    _find,
    _patterns,
    deterministic_verdict,
    load_recorded,
    read,
    read_probe,
    _probes,
)

SPECS = {slug: load_spec(slug) for slug in SLUGS}
ALL = pytest.mark.parametrize("slug", SLUGS)


def _ids(spec):
    return [c["id"] for c in spec["criteria"]]


@ALL
def test_recorded_verdicts_are_complete_binary_answers(slug):
    spec = SPECS[slug]
    recorded = load_recorded(spec)  # raises on a missing or non-boolean answer
    assert recorded, f"no judge verdicts recorded for {slug}"
    for per_judge in recorded.values():
        for verdict in per_judge.values():
            assert set(verdict.answers) == set(_ids(spec))


@ALL
def test_every_band_probe_parses_and_they_span_the_ladder(slug):
    """The probes exist because the PDF fixtures reach only two of the five bands."""
    spec = SPECS[slug]
    docs = {name: read_probe(path) for name, path in _probes(slug).items()}
    assert docs, f"no band probes found for {slug}"
    reached = set()
    for name, doc in docs.items():
        assert doc.answerable, f"{slug}/{name}: {doc.note}"
        verdict = deterministic_verdict(doc, spec)
        if verdict.complete(_ids(spec)):
            reached.add(band_of(verdict.answers, spec)["label"])
    recorded = load_recorded(spec)
    for name in docs:
        for verdict in recorded.get(name, {}).values():
            reached.add(band_of(verdict.answers, spec)["label"])
    assert len(reached) >= 4, f"{slug} probes only reach {sorted(reached)}"


@ALL
def test_the_deterministic_judge_answers_with_a_span_or_abstains(slug, fixtures):
    """Every `yes` carries the text behind it; a criterion with no rule channel abstains.

    The abstention is `AI-assisted coding fluency`'s C5. 04 set that category's
    rule_share to 0; answering `no` there would make an absent channel look like a
    judge that read the resume and found nothing.
    """
    spec = SPECS[slug]
    verdict = deterministic_verdict(read(fixtures["strong"]), spec)
    for criterion in spec["criteria"]:
        cid = criterion["id"]
        if criterion.get("deterministic", {}).get("kind") == "none":
            assert cid not in verdict.answers
            assert "unanswerable" in verdict.evidence[cid]
        else:
            assert cid in verdict.answers
            assert not verdict.answers[cid] or verdict.evidence[cid]


@ALL
def test_injected_hidden_text_never_answers_a_criterion(slug, fixtures):
    doc = read(fixtures["hidden_text"], score_degraded=True)
    assert "principal AI researcher" not in doc.text


@ALL
def test_documents_whose_roles_did_not_parse_are_withheld(slug, fixtures):
    assert read(fixtures["scanned"]).answerable is False
    assert read(fixtures["two_column"]).answerable is False
    assert read(fixtures["strong"]).answerable is True
    assert read(fixtures["two_column"], score_degraded=True).answerable is True


PO_SPEC = SPECS["production-ownership"]


def _doc(text):
    return Doc(text=text, resume=parse(text))


def test_named_in_finds_a_name_elsewhere_in_the_anchors_role():
    text = """Riley Tang
riley@example.com

EXPERIENCE
AI Engineer, Northwind Data                        Mar 2024 - Present
• Shipped the fraud detection service to production.
• Built the vLLM serving layer for it.
"""
    verdict = deterministic_verdict(_doc(text), PO_SPEC)
    assert verdict.answers["C2"] is True


def test_named_in_does_not_borrow_a_name_from_another_role():
    text = """Riley Tang
riley@example.com

EXPERIENCE
AI Engineer, Northwind Data                        Mar 2024 - Present
• Shipped the fraud detection service to production.

ML Engineer, Corvus Labs                           Jan 2022 - Jun 2023
• Built the vLLM serving layer for a different project.
"""
    verdict = deterministic_verdict(_doc(text), PO_SPEC)
    assert verdict.answers["C2"] is False


def test_named_in_does_not_borrow_a_name_via_a_duplicated_bullet():
    """A bullet repeated verbatim in a later role must not lend that role's name.

    `named_in` looks up the anchor's role by the bullet *text* found by C1, and the
    anchor bullet here is identical in both roles. On 1de8759 the text-keyed lookup
    resolves to whichever role's bullet was inserted last into the dict, so this
    case named the thing from the second role even though C1's anchor was the first
    role's occurrence.
    """
    text = """Riley Tang
riley@example.com

EXPERIENCE
AI Engineer, Northwind Data                        Mar 2024 - Present
• Shipped the platform to production.

ML Engineer, Corvus Labs                           Jan 2022 - Jun 2023
• Shipped the platform to production.
• Migrated it onto vLLM.
"""
    verdict = deterministic_verdict(_doc(text), PO_SPEC)
    assert verdict.answers["C2"] is False


RC_SPEC = SPECS["resume-craft"]


def _criterion(spec, cid):
    return next(c for c in spec["criteria"] if c["id"] == cid)


def test_operational_fact_aliases_hit_still_in_use():
    hit = _find(_patterns(_criterion(PO_SPEC, "C3")), ["The service is still in use."])
    assert hit is not None


def test_post_launch_work_aliases_do_not_hit_still_in_use():
    hit = _find(_patterns(_criterion(PO_SPEC, "C4")), ["The service is still in use."])
    assert hit is None


def test_resume_craft_c3_does_not_hit_for_enterprise_customers():
    hit = _find(_patterns(_criterion(RC_SPEC, "C3")), ["Built it for enterprise customers."])
    assert hit is None
