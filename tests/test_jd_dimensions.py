"""Dimension detection: phrases that describe a behaviour a posting expects rather
than naming a skill, so they can't be taxonomy terms.

Two jobs, per ticket 09. The corpus tests reproduce the counts `inventory.md` recorded
by hand, using verbatim posting text. The generalisation tests use phrasing that
appears nowhere in the six postings, because patterns fitted to the corpus that exists
would defeat the point of deriving weight from the corpus at all.
"""
import pytest

from ats.jd_dimensions import (
    CATEGORY_DIMENSIONS,
    categories_for,
    category_document_frequency,
    derived_weights,
    scan,
)

# Verbatim from corpus/jds/user/, one behaviour-bearing line per posting, quoted in
# docs/wayfinder/rubric-grounding/inventory.md.
AMEX = (
    "You will write production code, contribute to system design discussions, and "
    "help operate what you build after launch, with support and guidance from senior "
    "engineers. Build and extend agentic AI workflows that reason over context, call "
    "tools, and perform actions. Contribute to shared AI infrastructure such as LLM "
    "services, orchestration components, and evaluation or monitoring tooling. All "
    "systems are built to meet high standards for reliability, security, and "
    "auditability. Use of AI-assisted and agentic development tools for design, "
    "implementation, testing, debugging, and refactoring. 4+ years of professional "
    "software engineering experience."
)
ANTHROPIC = (
    "Serve as a specialist technical advisor to Anthropic customers as they deploy new "
    "products & workflows with our models: from discovery through deployment. Influence "
    "technical architecture decisions by developing customized pilots, prototypes, and "
    "evaluation suites. Production experience with LLMs including advanced prompt "
    "engineering, agent development and frameworks, evaluation frameworks. Comfortable "
    "with ambiguity. 4+ years of experience in technical roles."
)
EDRA = (
    "Own customer engagements from discovery and solution design through production, "
    "adoption, and expansion. Build agentic features for knowledge management. Build "
    "reliability and confidence systems-evaluation frameworks, confidence scoring. "
    "You've shipped something meaningful to production and can explain how it evolved. "
    "3+ years of professional experience."
)
FLUIDSTACK = (
    "Own models end to end, from problem framing and data through deployment, "
    "evaluation, and iteration in production. Ship agentic systems with real "
    "guardrails, authorization, audit, and evals. You've shipped ML or LLM features to "
    "production and owned them after launch. You've built evaluation harnesses that "
    "told you the truth about model quality before users did. You write "
    "production-quality code and work fluently with AI coding tools."
)
OPENAI = (
    "Design and iterate on agent behaviors across real-world coding tasks. Work closely "
    "with research to develop and run evals to measure agent performance, regressions, "
    "failure modes, and edge cases. Analyze failures in production and systematically "
    "improve robustness and reliability. Help define what 'good' looks like for agents "
    "completing complex tasks end-to-end."
)
RAMP = (
    "Design and ship customer-facing AI experiences end to end, from React UI through "
    "to the APIs and data contracts behind them. Build BI-tool-quality interfaces for "
    "agentic analysis: fast, dense, interactive, and trustworthy. Own complex "
    "client-side state and rendering challenges. Use the latest coding models and "
    "agentic workflows as a core part of how you ship every day. A track record of "
    "shipping polished, production-grade product experiences and owning them through "
    "ambiguity."
)
CORPUS = [AMEX, ANTHROPIC, EDRA, FLUIDSTACK, OPENAI, RAMP]


def test_reproduces_the_hand_read_category_counts():
    """inventory.md, read by hand: 6/6, 6/6, 5/6, 3/6. These counts are the test."""
    counts = category_document_frequency([scan(t) for t in CORPUS])
    assert counts == {
        "Production ownership": 6,
        "Agentic systems": 6,
        "Evaluation rigour": 5,
        "AI-assisted coding fluency": 3,
    }


def test_evaluation_misses_the_one_posting_that_does_not_ask_for_it():
    """5/6, not 6/6 -- ramp is a frontend role and says nothing about evals. A
    pattern set that reads 6/6 here is matching something that isn't there."""
    assert "evaluation" not in scan(RAMP)
    for other in (AMEX, ANTHROPIC, EDRA, FLUIDSTACK, OPENAI):
        assert "evaluation" in scan(other)


def test_ai_assisted_coding_is_the_three_postings_that_ask_for_it():
    assert {"ai_assisted_coding"} <= scan(AMEX)
    assert {"ai_assisted_coding"} <= scan(FLUIDSTACK)
    assert {"ai_assisted_coding"} <= scan(RAMP)
    # Building agents is not the same requirement as coding with them.
    assert "ai_assisted_coding" not in scan(OPENAI)
    assert "ai_assisted_coding" not in scan(EDRA)
    assert "ai_assisted_coding" not in scan(ANTHROPIC)


def test_ownership_reads_the_corpus_at_six_not_one():
    """The defect 09 exists for: the old patterns required `own` adjacent to
    production/lifecycle/end-to-end and read 1/6 against a corpus that is 6/6."""
    assert all("ownership" in scan(t) for t in CORPUS)


def test_experience_gate_is_the_three_postings_that_state_years():
    """inventory.md: amex 4+, anthropic 4+, edra 3+; the other three state none."""
    stated = [t for t in CORPUS if "experience_gate" in scan(t)]
    assert len(stated) == 3


# --- generalisation: phrasing that appears nowhere in the six postings ---

@pytest.mark.parametrize("dimension, text", [
    ("production", "Roll out changes to live traffic and carry the pager for them."),
    ("production", "Your work will be released to customers within the first month."),
    ("ownership", "You will steward each initiative from kickoff to rollout."),
    ("ownership", "Engineers here maintain what they ship long after launch."),
    ("reliability", "We hold ourselves to a high bar for uptime and error handling."),
    ("agentic", "Design autonomous workflows where the model decides which tool to call."),
    ("evaluation", "You will benchmark candidate models before any of them reach users."),
    ("ai_assisted_coding", "Pair with Cursor and Copilot daily; that is how we work."),
    ("seniority", "This is a greenfield team working with minimal supervision."),
])
def test_patterns_generalise_beyond_the_corpus(dimension, text):
    assert dimension in scan(text)


def test_a_posting_about_none_of_this_hits_nothing():
    assert scan(
        "Maintain our marketing website in WordPress and coordinate the content "
        "calendar with the brand team."
    ) == set()


def test_a_seventh_posting_moves_the_weights_with_nobody_editing_anything():
    """The whole reason weight is derived rather than authored. A seventh posting
    that asks for evals and nothing agentic lifts Evaluation rigour's share and cuts
    everyone else's, with no change to this file or to weights.toml."""
    seventh = (
        "You will benchmark model quality continuously and publish the results. "
        "Everything you write is released to customers and you carry the pager for it."
    )
    before = category_document_frequency([scan(t) for t in CORPUS])
    after = category_document_frequency([scan(t) for t in CORPUS + [seventh]])

    assert before["Evaluation rigour"] == 5 and after["Evaluation rigour"] == 6
    assert after["Agentic systems"] == 6  # unmoved: the seventh says nothing agentic

    w_before = derived_weights(before, total=6, budget=40.0)
    w_after = derived_weights(after, total=7, budget=40.0)
    assert w_after["Evaluation rigour"] > w_before["Evaluation rigour"]
    assert w_after["Agentic systems"] < w_before["Agentic systems"]
    assert sum(w_before.values()) == pytest.approx(40.0, abs=0.05)
    assert sum(w_after.values()) == pytest.approx(40.0, abs=0.05)


def test_a_behaviour_no_posting_states_earns_no_points():
    counts = {"Production ownership": 3, "Agentic systems": 0}
    weights = derived_weights(counts, total=3, budget=30.0)
    assert weights["Agentic systems"] == 0.0
    assert weights["Production ownership"] == pytest.approx(30.0)


def test_an_empty_corpus_derives_nothing_rather_than_dividing_by_zero():
    counts = {c: 0 for c in CATEGORY_DIMENSIONS}
    assert set(derived_weights(counts, total=0, budget=40.0).values()) == {0.0}
    assert set(derived_weights(counts, total=6, budget=40.0).values()) == {0.0}


def test_a_category_counts_a_posting_once_however_many_of_its_behaviours_it_states():
    """Production ownership is the union of three dimensions. A posting stating all
    three is still one document."""
    both = {"production", "ownership", "reliability"}
    assert categories_for(both) == {"Production ownership"}
    assert category_document_frequency([both])["Production ownership"] == 1
