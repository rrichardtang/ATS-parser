"""The worst-case cost a run is refused on, with no provider and no network."""
import openai
import pytest

from ats import budget, llm
from ats.llm import Provider

CLAUDE = Provider("anthropic", "k", "claude-sonnet-5")
OPENAI = Provider("openai", "k", "gpt-6-luna")
TEN_DOCUMENTS = [5600] * 10


def _calls(n):
    return {"anthropic": n, "openai": n}


def test_ten_documents_batched_at_the_default_cap_are_refused():
    costs = budget.worst_case([CLAUDE], TEN_DOCUMENTS, _calls(2), True, None)
    assert costs[CLAUDE.label] == pytest.approx(6.40 + 20 * 5600 * 1.25 / 1e6)

    fits, report = budget.verdict([CLAUDE], TEN_DOCUMENTS, _calls(2), True, None, 3.0)
    assert not fits
    assert "largest --max-tokens that fits these documents is 28600" in report


def test_a_lowered_cap_fits_the_same_run():
    lowered = Provider("anthropic", "k", "claude-sonnet-5", 25000)
    fits, report = budget.verdict([lowered], TEN_DOCUMENTS, _calls(2), True, None, 3.0)
    assert fits, report
    assert "$2.64" in report


def test_live_costs_double_batch_twice_over_for_price_and_repair():
    live = budget.worst_case([CLAUDE], TEN_DOCUMENTS, _calls(2), False, None)[CLAUDE.label]
    batched = budget.worst_case([CLAUDE], TEN_DOCUMENTS, _calls(2), True, None)[CLAUDE.label]
    assert live == pytest.approx(4 * batched)


def test_openai_is_refused_without_a_price_and_costed_with_one():
    fits, report = budget.verdict([CLAUDE, OPENAI], [3000], _calls(1), True, None, 100.0)
    assert not fits and "--openai-price" in report and "--claude-only" in report

    costs = budget.worst_case([OPENAI], [3000], _calls(1), True, (1.0, 8.0))
    # Repair retry x (1 + the SDK's timeout retries): OpenAI does not stream.
    attempts = 2 * (1 + openai.DEFAULT_MAX_RETRIES)
    assert costs[OPENAI.label] == pytest.approx(
        attempts * (3000 * 1.0 + llm.MAX_TOKENS * 8.0) / 1e6)


@pytest.mark.parametrize("providers, samples, price", [
    ([Provider("anthropic", "k", "claude-sonnet-5", -10**7), OPENAI], 2, (5.0, 40.0)),
    ([Provider("anthropic", "k", "claude-sonnet-5", 0)], 2, None),
    ([CLAUDE, OPENAI], 2, (-1.0, -1.0)),
    ([CLAUDE], -2, None),
])
def test_a_negative_cap_price_or_sample_count_is_refused(providers, samples, price):
    """Any of them makes a negative cost that would offset another provider's."""
    with pytest.raises(ValueError):
        budget.verdict(providers, [5000] * 7, _calls(samples), True, price, 3.0)


def test_skipped_documents_cost_nothing():
    assert budget.worst_case([CLAUDE], [], _calls(2), False, None) == {CLAUDE.label: 0.0}


def test_openai_votes_multiply_its_calls():
    """The harness's luna samples are voted: 2 samples x 3 votes is 6 real calls."""
    voted = budget.worst_case([OPENAI], [3000], {"openai": 6}, True, (0.10, 0.50))
    single = budget.worst_case([OPENAI], [3000], {"openai": 1}, True, (0.10, 0.50))
    assert voted[OPENAI.label] == pytest.approx(6 * single[OPENAI.label])


def test_a_harness_openai_try_without_sdk_retries_is_two_attempts():
    harness = Provider("openai", "k", "gpt-6-luna", openai_max_retries=0)
    costs = budget.worst_case([harness], [3000], {"openai": 1}, True, (1.0, 8.0))
    assert costs[harness.label] == pytest.approx(
        budget.LIVE_ATTEMPTS * (3000 * 1.0 + llm.MAX_TOKENS * 8.0) / 1e6)


def test_an_openai_worst_case_uses_the_cap_the_provider_sends():
    raised = Provider("openai", "k", "gpt-6-luna", openai_max_retries=0,
                      openai_max_tokens=24000)
    costs = budget.worst_case([raised], [3000], {"openai": 1}, True, (1.0, 8.0))
    assert costs[raised.label] == pytest.approx(
        budget.LIVE_ATTEMPTS * (3000 * 1.0 + 24000 * 8.0) / 1e6)


def test_an_openai_only_run_over_budget_is_not_told_about_claudes_cap():
    fits, report = budget.verdict([OPENAI], TEN_DOCUMENTS, {"openai": 6}, False,
                                  (0.10, 0.50), 0.01)
    assert not fits
    assert "--openai-max-tokens" in report and "--max-tokens" not in report.replace(
        "--openai-max-tokens", "")
