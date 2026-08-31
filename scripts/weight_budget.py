"""Score the seven fixtures under the new rubric, at every candidate weight budget.

Ticket 02 of the migration map has two questions and refuses to answer either in the
abstract: how many of the composite's 100 points the four corpus-derived categories
share, and whether that budget is split in proportion to document frequency (6:6:5:3)
or in tiers. This script is the output it wanted to be answered against.

It is a **measurement, not a scoring path**. Nothing in `ats/` imports it. It assembles
the new rubric out of parts that already exist and are already decided:

  * the rules that run today (`pipeline.deterministic`), refiled into the new
    categories by `rule-mapping.md` (07) with 12's rulings applied, and with the
    advice-only rules no longer deducting;
  * a band per judged category from `ats/rubric.band_of`, over the criterion answers
    the recorded model judge gave in `criteria/judgments/` -- the same answers 05, 11
    and 12 measured agreement on;
  * `score.py`'s own blend, `rule_score * rule_share + band * (1 - rule_share)`, with
    each category's `rule_share` read from its spec.

The old column is not modelled at all: it is `score.build` on the same findings, which
is literally what the program does today with no provider credentials.

    python scripts/weight_budget.py              # the composite table, every candidate
    python scripts/weight_budget.py --categories # per-category scores at one budget
    python scripts/weight_budget.py --rules      # what each rule costs, old vs new
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ats import config, jd_dimensions  # noqa: E402
from ats.models import Category, Finding  # noqa: E402
from ats.pipeline import deterministic, resolve_target_title  # noqa: E402
from ats.extract import extract  # noqa: E402
from ats.rubric import band_of, load_spec  # noqa: E402
from ats.score import build  # noqa: E402
from ats.sections import parse  # noqa: E402
from scripts.criteria_probe import load_recorded  # noqa: E402

# --- The new category set -----------------------------------------------------------
#
# Four derived (04: document frequency sets the weight) and four authored (04: not in
# the corpus, so no df exists to derive from). `Recruiter scan` and `Writing quality`
# are the two the old set loses; 12 put craft under Gate.RECRUITER, which is where both
# of them sat, so their 15 + 10 is the authored block's craft line at today's numbers.
DERIVED = ("Production ownership", "Agentic systems", "Evaluation rigour",
           "AI-assisted coding fluency")
CRAFT = "Resume craft"
# Held fixed across every candidate: none of them is in the corpus and no ticket has
# reopened their numbers, so the budget question is behaviour weight against craft
# weight and nothing else.
FIXED_AUTHORED = {"Parseability": 15.0, "Structure & formatting": 5.0,
                  "Title & seniority alignment": 5.0}

SLUG_OF = {
    "Production ownership": "production-ownership",
    "Agentic systems": "agentic-systems",
    "Evaluation rigour": "evaluation-rigour",
    "AI-assisted coding fluency": "ai-assisted-coding-fluency",
    CRAFT: "resume-craft",
}

# --- Where every rule files, and whether it still deducts ----------------------------
#
# `rule-mapping.md` §1 for the moves, §2 for advice-only, §3 for the collisions, §4 for
# the retirement -- and ticket 12's rulings on the three 07 left conditional, which are
# later and win. Anything not named here keeps its category by the old-to-new identity
# at the bottom of `_new_category`; an unmapped rule raises rather than defaulting,
# because a rule silently landing in the wrong category is exactly the error this table
# exists to prevent.
REFILED = {
    "cred/no-production": "Production ownership",
    "content/ownership": "Production ownership",
    "cred/notebook-only": "Production ownership",
    "cred/no-evaluation": "Evaluation rigour",
    "contact/no-github": "Structure & formatting",
    "scan/no-identity-above-fold": CRAFT,
    "scan/no-evidence-above-fold": CRAFT,
    "scan/no-summary": CRAFT,
    "scan/experience-outranked": CRAFT,
    "scan/unexplained-pivot": CRAFT,
    "content/passive-voice": CRAFT,
    "content/first-person": CRAFT,
    "content/long-bullet": CRAFT,
    "content/duplicate-bullet": CRAFT,
    "content/weak-opener": CRAFT,
    "content/bullet-invariants": CRAFT,
    "content/quantification": CRAFT,
    "cred/unlinked-projects": CRAFT,
    "kw/over-repetition": CRAFT,
    "kw/skills-dump": CRAFT,
    "kw/soft-skill-padding": CRAFT,
}

# Fires, prints, costs nothing. Tool coverage (§2), the two collision losers (§3), and
# 12's two rulings.
ADVICE_ONLY = {
    "cred/notebook-only",        # §3.1 -- a second price for C1's absence
    "content/quantification",    # 12 -- measurability is priced in two other categories
    "cred/unlinked-projects",    # 12 -- no craft criterion answers verifiability
    "jd/missing-core", "jd/missing-secondary", "jd/missing-named-tools",
    "kw/unsupported-skills",
}
RETIRED = {"cred/no-named-models"}          # §4

# Old category -> new, for the rules whose category simply survives 04.
CARRIED = {
    Category.PARSEABILITY: "Parseability",
    Category.STRUCTURE: "Structure & formatting",
    Category.TITLE: "Title & seniority alignment",
    Category.WRITING: CRAFT,                # every slop/* rule arrives this way
    Category.RECRUITER_SCAN: CRAFT,
}

FIXTURES = ("strong", "slop", "two_column", "hidden_text", "scanned", "no_phone",
            "buried_evidence")


def _new_category(finding: Finding) -> str:
    """Where a finding lands, or that it lands nowhere.

    A rule that no longer deducts has no category at all -- 07 §2 gives advice-only
    findings a gate and no category, and this map's 04 implements it. Naming one anyway
    would put a number beside a finding that costs nothing.
    """
    if finding.rule_id in RETIRED:
        return "(retired)"
    if not _deducts(finding.rule_id):
        return "(advice-only)"
    if finding.rule_id in REFILED:
        return REFILED[finding.rule_id]
    if finding.category in CARRIED:
        return CARRIED[finding.category]
    raise SystemExit(f"{finding.rule_id} ({finding.category}) is in no mapping")


def _deducts(rule_id: str) -> bool:
    return not (rule_id in ADVICE_ONLY or rule_id in RETIRED
                or rule_id.startswith("kw/thin-"))


# --- Weights ------------------------------------------------------------------------


def proportional(budget: float) -> dict[str, float]:
    """`jd_dimensions.derived_weights` on the digest's own counts. 6:6:5:3."""
    digest = config.jd_digest()["category_document_frequency"]
    counts = {name: digest[name]["count"] for name in DERIVED}
    total = max(digest[name]["total"] for name in DERIVED)
    return jd_dimensions.derived_weights(counts, total, budget)


FLOOR = 2 / 3


def floored(budget: float) -> dict[str, float]:
    """Proportional, but no category falls below two thirds of the largest share.

    02's objection, made arithmetic: document frequency cannot tell a hard expectation
    stated in three postings from a passing mention in three, and ramp states
    AI-assisted coding as the former -- *"this is how the team works, and we expect you
    to be excellent at it"*. Straight proportion prices that at half of `Agentic
    systems`, which is a claim about the behaviour that six documents cannot support.

    The floor is deliberately not a re-ranking: the corpus still orders the four, it
    just stops being read to one decimal place off six postings. A category no posting
    states still gets 0 -- the floor lifts a stated behaviour off the bottom, it does
    not invent one.
    """
    digest = config.jd_digest()["category_document_frequency"]
    raw = {name: digest[name]["count"] / digest[name]["total"] for name in DERIVED}
    ceiling = max(raw.values())
    shares = {name: (max(share, FLOOR * ceiling) if share else 0.0)
              for name, share in raw.items()}
    denominator = sum(shares.values())
    return {name: round(budget * share / denominator, 2)
            for name, share in shares.items()}


def weights_for(budget: float, split) -> dict[str, float]:
    """The whole eight-category set. Craft absorbs whatever the budget leaves.

    Parseability, Structure and Title are held at today's numbers, so a budget of 50
    reproduces today's authored block exactly and every other candidate is visibly a
    trade of craft weight for behaviour weight.
    """
    weights = dict(FIXED_AUTHORED)
    weights[CRAFT] = round(100.0 - budget - sum(FIXED_AUTHORED.values()), 2)
    weights.update(split(budget))
    return weights


# --- Scoring ------------------------------------------------------------------------


def findings_for(name: str, path: Path) -> list[Finding]:
    doc = extract(str(path))
    resume = parse(doc.text)
    return deterministic(doc, resume, "", resolve_target_title(""))


def judged_bands(name: str) -> dict[str, tuple[str, float] | None]:
    """The recorded model judge's band per category, or None where it did not judge.

    The model judge is the only one that answers all five: the deterministic judge
    abstains on `AI-assisted coding fluency` C5 by construction (04's rule_share 0), so
    it can never name a band there. Using it for the other four and the model for the
    fifth would mix two judges inside one composite, which is the thing a composite
    must not do.
    """
    out: dict[str, tuple[str, float] | None] = {}
    for category, slug in SLUG_OF.items():
        spec = load_spec(slug)
        ids = [c["id"] for c in spec["criteria"]]
        verdict = load_recorded(spec).get(name, {}).get("model-claude")
        if verdict is None or not verdict.complete(ids):
            out[category] = None
            continue
        band = band_of(verdict.answers, spec)
        out[category] = (band["label"], float(band["value"]))
    return out


def new_report(findings: list[Finding], bands: dict, weights: dict[str, float]) -> dict:
    """The new composite, by `score.py`'s own arithmetic on the new category set.

    Deductions, the anti-hard-gate clamp and the fraud cap are all the ones that run
    today; what changes is which category a finding lands in, whether it deducts at
    all, and that a judged category's score is a blend with its band rather than a
    rule score alone.
    """
    points = config.severity_points()
    deductions = {category: 0.0 for category in weights}
    for finding in findings:
        if not _deducts(finding.rule_id):
            continue
        category = _new_category(finding)
        raw = points[finding.severity] * config.dimension_multiplier(finding.rule_id)
        if finding.rule_id not in {"parse/hidden-text"}:
            raw = min(raw, weights[category])
        deductions[category] += raw

    unreadable = any(f.rule_id == "parse/no-text-layer" for f in findings)
    scores, notes = {}, {}
    for category, weight in weights.items():
        rule_score = 0.0 if unreadable else max(0.0, 100.0 - deductions[category])
        if category in SLUG_OF:
            share = float(load_spec(SLUG_OF[category])["rule_share"])
            band = bands.get(category)
            if band is None:
                notes[category] = "no band"
            elif unreadable:
                notes[category] = "withheld"
            else:
                rule_score = rule_score * share + band[1] * (1 - share)
                notes[category] = band[0]
        scores[category] = round(rule_score, 1)

    composite = sum(scores[c] * w for c, w in weights.items()) / sum(weights.values())
    if any(f.rule_id == "parse/hidden-text" for f in findings):
        composite = min(composite, float(config.scoring()["fraud_cap"]))
    if unreadable:
        composite = min(composite, 15.0)
    return {"composite": round(max(0.0, min(100.0, composite)), 1),
            "scores": scores, "notes": notes, "deductions": deductions}


# --- Reports ------------------------------------------------------------------------

CANDIDATES = [
    ("40 proportional", 40.0, proportional),
    ("45 proportional", 45.0, proportional),
    ("50 proportional", 50.0, proportional),
    ("55 proportional", 55.0, proportional),
    ("60 proportional", 60.0, proportional),
    ("50 floored", 50.0, floored),
    ("40 floored", 40.0, floored),
]


def _grade(value: float) -> str:
    for threshold, letter in [(90, "A"), (80, "B"), (70, "C"), (60, "D"), (0, "F")]:
        if value >= threshold:
            return letter
    return "F"


def composite_table(runs: dict) -> None:
    print("=== composite per fixture: today's rubric (rules only) vs each candidate ===")
    header = f"{'fixture':<17}{'old':>7}" + "".join(f"{label:>17}" for label, _, _ in CANDIDATES)
    print(header)
    for name in FIXTURES:
        run = runs[name]
        row = f"{name:<17}{run['old']:>6.1f}{_grade(run['old']):>1}"
        for label, _, _ in CANDIDATES:
            value = run["new"][label]["composite"]
            row += f"{value:>15.1f} {_grade(value):<1}"
        print(row)

    print("\n--- rank order, worst first ---")
    def order(key):
        return " < ".join(sorted(FIXTURES, key=key))
    print(f"{'old':<17}{order(lambda n: runs[n]['old'])}")
    for label, _, _ in CANDIDATES:
        print(f"{label:<17}{order(lambda n: runs[n]['new'][label]['composite'])}")

    print("\n--- spread between the candidates, per fixture ---")
    print(f"{'fixture':<17}{'min':>8}{'max':>8}{'range':>8}   what moves it")
    for name in FIXTURES:
        values = [runs[name]["new"][label]["composite"] for label, _, _ in CANDIDATES]
        low, high = min(values), max(values)
        craft = runs[name]["new"]["50 proportional"]["scores"][CRAFT]
        behaviour = sum(runs[name]["new"]["50 proportional"]["scores"][c] for c in DERIVED) / 4
        print(f"{name:<17}{low:>8.1f}{high:>8.1f}{high - low:>8.1f}   "
              f"craft {craft:.0f} vs behaviour {behaviour:.0f}")


def category_table(runs: dict, label: str) -> None:
    weights = runs["_weights"][label]
    print(f"=== per-category score at {label} ===")
    print(f"{'category':<30}{'weight':>8}" + "".join(f"{n:>14}" for n in FIXTURES))
    for category in list(FIXED_AUTHORED) + [CRAFT] + list(DERIVED):
        row = f"{category:<30}{weights[category]:>8.2f}"
        for name in FIXTURES:
            report = runs[name]["new"][label]
            note = report["notes"].get(category, "")
            cell = f"{report['scores'][category]:.0f}" + (f" {note}" if note else "")
            row += f"{cell:>14}"
        print(row)
    row = f"{'COMPOSITE':<30}{sum(weights.values()):>8.2f}"
    for name in FIXTURES:
        row += f"{runs[name]['new'][label]['composite']:>14.1f}"
    print(row)
    row = f"{'  (today, rules only)':<30}{'':>8}"
    for name in FIXTURES:
        row += f"{runs[name]['old']:>14.1f}"
    print(row)


def rules_table(runs: dict) -> None:
    print("=== every rule that fired on the fixtures, and where it goes ===")
    print(f"{'rule':<30}{'old category':<30}{'new category':<30}{'deducts':>8}")
    seen = {}
    for name in FIXTURES:
        for finding in runs[name]["findings"]:
            seen[finding.rule_id] = finding
    for rule_id, finding in sorted(seen.items()):
        mark = "yes" if _deducts(rule_id) else ("retired" if rule_id in RETIRED else "advice")
        print(f"{rule_id:<30}{finding.category.value:<30}"
              f"{_new_category(finding):<30}{mark:>8}")


def tolerance_table() -> None:
    """What one criterion split costs the composite, per candidate.

    This is the half of the question the seven fixtures cannot answer, and it is not
    abstract: the inherited acceptance test is a composite tolerance -- two judges
    within 5 points, over 8 fails -- and a weight set decides how much of that budget
    one disagreement spends. A criterion split moves the band by up to its `widest
    move` (the leverage table), the band moves the category score by the gap between
    band values, and the weight turns that into composite points:

        composite move = band gap * (1 - rule_share) * weight / 100

    `Agentic systems` and `AI-assisted coding fluency` are the exposed ones: at
    `rule_share` 0 there is no rule channel to average the disagreement down, so the
    whole band move reaches the composite (07 §5 is why they are 0, and it is a
    correction that will stand until 09 gives Agentic systems a dimension).
    """
    print("=== what one criterion split costs the composite ===")
    print("Acceptance bar (inherited): two judges within 5 composite points; over 8 fails.\n")
    specs = {category: load_spec(slug) for category, slug in SLUG_OF.items()}
    print(f"{'':<17}" + "".join(f"{c[:26]:>27}" for c in SLUG_OF) + f"{'worst':>8}")
    print(f"{'candidate':<17}" + "".join(f"{'gate / cheapest':>27}" for _ in SLUG_OF)
          + f"{'total':>8}")
    for label, budget, split in CANDIDATES:
        weights = weights_for(budget, split)
        row, worst = f"{label:<17}", 0.0
        for category, spec in specs.items():
            values = [b["value"] for b in spec["bands"]]
            share = 1 - float(spec["rule_share"])
            widest = max(v - u for u, v in zip(values, values[1:]))
            gate = (values[-1] - values[0]) * share * weights[category] / 100
            cheap = widest * share * weights[category] / 100
            worst = max(worst, gate)
            row += f"{f'{gate:.1f} / {cheap:.1f}':>27}"
        print(row + f"{worst:>8.1f}")
    print("\n'gate' is a split on the criterion with the widest reach (C1 in the four "
          "gated\ncategories, any of the five in the counted one); 'cheapest' is one "
          "adjacent band.")


def weight_table() -> None:
    print("=== the candidate weight sets ===")
    print(f"{'':<17}" + "".join(f"{c:>28}" for c in list(DERIVED)) + f"{CRAFT:>16}")
    for label, budget, split in CANDIDATES:
        weights = weights_for(budget, split)
        row = f"{label:<17}"
        for category in DERIVED:
            row += f"{weights[category]:>28.2f}"
        row += f"{weights[CRAFT]:>16.2f}"
        print(row)
    print(f"\nHeld fixed in every candidate: "
          + ", ".join(f"{k} {v:.0f}" for k, v in FIXED_AUTHORED.items()) + ".")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--categories", metavar="CANDIDATE", nargs="?",
                        const="50 proportional", default=None,
                        help="per-category scores at one candidate (default 50 proportional)")
    parser.add_argument("--rules", action="store_true",
                        help="where each rule that fired refiles, and whether it deducts")
    parser.add_argument("--tolerance", action="store_true",
                        help="what one criterion split costs the composite, per candidate")
    parser.add_argument("--weights", action="store_true",
                        help="the candidate weight sets and nothing else")
    args = parser.parse_args()

    if args.weights:
        weight_table()
        return 0

    if args.tolerance:
        tolerance_table()
        return 0

    from tests.make_fixtures import build_all
    paths = build_all()

    runs: dict = {"_weights": {label: weights_for(budget, split)
                              for label, budget, split in CANDIDATES}}
    for name in FIXTURES:
        findings = findings_for(name, paths[name])
        bands = judged_bands(name)
        runs[name] = {
            "findings": findings,
            "old": build(list(findings)).composite,
            "new": {label: new_report(findings, bands, runs["_weights"][label])
                    for label, _, _ in CANDIDATES},
        }

    if args.rules:
        rules_table(runs)
    elif args.categories:
        category_table(runs, args.categories)
    else:
        weight_table()
        print()
        composite_table(runs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
