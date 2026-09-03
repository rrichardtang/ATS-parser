"""What the chosen weight budget costs in judge agreement.

Ticket 02 chose the budget -- 50 points across the four corpus-derived categories,
split in proportion to document frequency -- from a table this script used to print by
modelling the new rubric beside the old one. **Ticket 03 made the model redundant**:
the category set, the weights and the per-category `rule_share` are what `ats/` runs
now, so a script carrying its own copy of the mapping would only be a second version of
it, drifting. The composite tables 02 argued from are recorded verbatim in
`docs/wayfinder/rubric-migration/weight-budget.md`, printed on the last commit before
the swap.

What survives is the half the program still cannot answer, because it needs two judges
and a run only ever has one: **how much of the acceptance tolerance a single criterion
disagreement spends.** The inherited bar is a composite tolerance -- two judges within
5 points, over 8 fails -- and the weights decide what one split costs:

    composite move = band gap * (1 - rule_share) * weight / assessed weight

Everything on the right comes from the program: `config.category_weights()`,
`score.rule_shares()`, and the band values in each category's spec.

    python scripts/weight_budget.py             # the tolerance table
    python scripts/weight_budget.py --weights   # the live weights, and where each comes from
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ats import config, rubric  # noqa: E402
from ats.models import DERIVED_CATEGORIES, JUDGED_CATEGORIES  # noqa: E402
from ats.score import rule_shares  # noqa: E402

# The inherited acceptance test, from the rubric-grounding map.
TOLERANCE, FAIL = 5.0, 8.0


def weight_table() -> None:
    weights = config.category_weights()
    counts, postings = config.derived_document_frequency()
    budget = float(config.load()["derived"]["budget"])
    shares = rule_shares()

    print(f"=== category weights ({budget:.0f} of 100 points derived, "
          f"over {postings} postings) ===")
    print(f"{'category':<30}{'weight':>8}{'source':>14}{'rule_share':>12}")
    for category, weight in weights.items():
        source = (f"df {counts[category.value]}/{postings}"
                  if category in DERIVED_CATEGORIES else "authored")
        share = f"{shares[category]:.1f}" if category in shares else "-"
        print(f"{category.value:<30}{weight:>8.2f}{source:>14}{share:>12}")
    print(f"{'':<30}{sum(weights.values()):>8.2f}")


def tolerance_table() -> None:
    """What one criterion split costs the composite, per judged category.

    `Agentic systems` and `AI-assisted coding fluency` are the exposed ones: at
    `rule_share` 0 there is no rule channel to average a disagreement down, so the
    whole band move reaches the composite. 07 §5 is why they are 0 -- a `rule_share`
    above 0 with no deducting rule scores against a constant, not a channel.

    The denominator is the assessed weight. A judged category nobody answered is left
    out of the composite entirely, so these are the numbers a run with all five
    answered actually sees.
    """
    weights = config.category_weights()
    shares = rule_shares()
    slugs = rubric.slug_by_category()
    total = sum(weights.values())

    print("=== what one criterion split costs the composite ===")
    print(f"Acceptance bar: two judges within {TOLERANCE:.0f} composite points; "
          f"over {FAIL:.0f} fails.\n")
    print(f"{'category':<30}{'weight':>8}{'share':>7}{'widest split':>14}"
          f"{'one band':>10}   verdict")
    worst = 0.0
    for category in JUDGED_CATEGORIES:
        spec = rubric.load_spec(slugs[category.value])
        values = [band["value"] for band in spec["bands"]]
        reach = 1 - shares[category]
        gate = (values[-1] - values[0]) * reach * weights[category] / total
        cheapest = (max(v - u for u, v in zip(values, values[1:]))
                    * reach * weights[category] / total)
        worst = max(worst, gate)
        verdict = "FAIL" if gate > FAIL else ("LOOK" if gate > TOLERANCE else "PASS")
        print(f"{category.value:<30}{weights[category]:>8.2f}{shares[category]:>7.1f}"
              f"{gate:>14.1f}{cheapest:>10.1f}   {verdict}")
    print(f"\nWorst single split: {worst:.1f} composite points.")
    print("'widest split' is a disagreement on the criterion with the longest reach "
          "(C1 in the\nfour gated categories); 'one band' is an adjacent-band "
          "disagreement, which is the only\nkind any judge pair has actually produced.")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--weights", action="store_true",
                        help="the live weights, and where each one comes from")
    args = parser.parse_args()
    if args.weights:
        weight_table()
    else:
        tolerance_table()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
