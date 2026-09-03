"""Slop patterns, with a negative fixture for every positive one.

The negatives matter more than the positives. A slop detector that fires on
ordinary formal writing makes people delete good sentences, and "eval harness"
must never be flagged just because "harness" is on a banned-word list.
"""
import pytest

from ats.sections import parse
from ats.slop import analyze
from ats.slop_patterns import PATTERNS, BY_ID

POSITIVE = {
    "slop/banned-word": "Leveraged cutting-edge tooling to deliver robust systems.",
    "slop/superficial-analysis": "Shipped the API, highlighting my commitment to quality.",
    "slop/importance-puffery": "This work stands as a testament to engineering rigour.",
    "slop/fake-strong-verb": "The app serves as a centralized hub for sponsor management.",
    "slop/weasel-attribution": "Experts agree this approach is the industry standard.",
    "slop/empty-phrase": "At the end of the day, the model has to ship.",
    "slop/binary-contrast": "It's not just about code. It's about impact.",
    "slop/throat-clearing": "Here's the thing: the eval was wrong.",
    "slop/faux-insight": "What most people get wrong is the retrieval step.",
    "slop/rhetorical-setup": "What if I told you retrieval was the bottleneck?",
    "slop/metadiscourse": "It's worth noting that the latency halved.",
    "slop/summary-recap": "In conclusion, the system works well.",
    "slop/negative-listing": "Not a framework. Not a library. A protocol.",
}

# Ordinary technical writing that must NOT fire.
NEGATIVE = [
    "Built the eval harness for our RAG pipeline with 900 labelled QA pairs.",
    "Cut p99 inference latency 380ms to 95ms by moving Llama-3-8B to vLLM.",
    "Tested robustness to malformed input across 12k requests.",
    "Ported serving from Flask to FastAPI with async batching.",
    "Wrote the retraining loop that caught a 9-point AUC regression.",
    "Shipped a LoRA fine-tune of Mistral-7B for ticket triage.",
]


@pytest.mark.parametrize("pattern_id,text", sorted(POSITIVE.items()))
def test_pattern_fires_on_its_positive_case(pattern_id, text):
    assert BY_ID[pattern_id].find(text), f"{pattern_id} did not fire"


@pytest.mark.parametrize("text", NEGATIVE)
def test_patterns_stay_quiet_on_real_technical_writing(text):
    resume = parse(f"EXPERIENCE\nAI Engineer, Acme  Mar 2024 - Present\n• {text}\n")
    findings = analyze(resume, text)
    assert findings == [], f"false positives: {[f.rule_id for f in findings]}"


def test_eval_harness_is_not_slop():
    """'harness' is a banned word in the source skill, but 'eval harness' is the
    ordinary technical name for the thing."""
    resume = parse(
        "EXPERIENCE\nAI Engineer, Acme  Mar 2024 - Present\n"
        "• Built the eval harness that gates releases on 900 labelled pairs.\n"
    )
    assert not [f for f in analyze(resume, "") if f.rule_id == "slop/banned-word"]


def test_every_pattern_declares_scope_and_provenance():
    for pattern in PATTERNS:
        assert pattern.scope is not None
        assert pattern.provenance is not None
        assert pattern.fix, f"{pattern.id} has no fix text"


def test_findings_always_carry_evidence():
    """Per the source skill: named patterns with a quote, never a bare accusation."""
    text = "Leveraged cutting-edge AI to deliver robust and scalable solutions."
    resume = parse(f"EXPERIENCE\nEngineer, Acme  Mar 2024 - Present\n• {text}\n")
    findings = analyze(resume, text)
    assert findings
    assert all(f.evidence.strip() for f in findings)


def test_no_ai_likelihood_score_anywhere(analyzed):
    """The source skill's rule: detectors guess, named patterns are evidence.

    Nothing in the report may claim a probability that AI wrote the resume.
    """
    banned = ("ai-generated", "ai likelihood", "% ai", "written by ai", "ai score",
              "probability", "ai-written")
    for name, report in analyzed.items():
        blob = " ".join(
            [f.message + f.fix for f in report.findings] + report.notes
        ).lower()
        for phrase in banned:
            assert phrase not in blob, f"{name} report claims AI authorship: {phrase}"
