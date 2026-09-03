"""Decompose a saved agreement run into the parts that need different fixes.

`scripts/agreement_harness.py` prints spread, noise floor and alpha. It cannot say
*what kind* of disagreement it found, and on the first real run the kinds turned out
to need opposite remedies:

  * a systematic calibration offset -- one provider scoring uniformly higher, which
    no rubric wording repairs and which the 04 output form removes entirely;
  * genuine per-category disagreement left after the offset is removed;
  * and a findings table that read as near-total disagreement, because it was keyed
    on a name the model invents fresh each time rather than on the place it points at.

    python scripts/baseline_analysis.py runs/agreement-....json
    python scripts/baseline_analysis.py --extract runs/....json docs/.../run-summary.json

`--extract` writes the numbers back out with every span of resume text removed, so a
run's arithmetic stays checkable after the raw file (which quotes resumes verbatim,
and is gitignored for that reason) is gone.
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

# Resumes named in a run are people. The extract keeps the synthetic fixtures under
# their own names -- they are checked into the repo -- and anonymises anything else.
FIXTURES = {"strong", "slop", "two_column", "hidden_text", "scanned", "no_phone",
            "buried_evidence"}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip().lower()


def _provider(label: str) -> str:
    return label.split(":")[0]


def scored(run: dict) -> list[dict]:
    return [r for r in run["resumes"] if not r.get("skipped")]


def categories_of(run: dict) -> list[str]:
    for resume in scored(run):
        for judgment in resume["judgments"]:
            return list(judgment["categories"])
    return []


def means(run: dict) -> dict[tuple[str, str], dict[str, float]]:
    """(resume, category) -> provider -> mean score across that provider's samples."""
    out: dict[tuple[str, str], dict[str, float]] = defaultdict(dict)
    for resume in scored(run):
        per: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
        for judgment in resume["judgments"]:
            for category, entry in judgment["categories"].items():
                per[_provider(judgment["provider"])][category].append(float(entry["score"]))
        for provider, by_category in per.items():
            for category, values in by_category.items():
                out[(resume["name"], category)][provider] = statistics.mean(values)
    return out


def _spearman(left: list[float], right: list[float]) -> float | None:
    if len(left) < 3:
        return None

    def rank(values: list[float]) -> list[float]:
        order = sorted(range(len(values)), key=lambda i: values[i])
        ranks = [0.0] * len(values)
        for position, index in enumerate(order):
            ranks[index] = float(position)
        return ranks

    a, b = rank(left), rank(right)
    n = len(a)
    return 1 - 6 * sum((x - y) ** 2 for x, y in zip(a, b)) / (n * (n * n - 1))


def offset_table(run: dict) -> list[tuple]:
    """Per category: the offset between providers, what survives removing it, and rank."""
    table = means(run)
    providers = sorted({p for cell in table.values() for p in cell})
    if len(providers) != 2:
        return []
    low, high = providers
    rows = []
    for category in categories_of(run):
        pairs = [(cell[low], cell[high]) for (_, c), cell in table.items()
                 if c == category and len(cell) == 2]
        if not pairs:
            continue
        diffs = [b - a for a, b in pairs]
        offset = statistics.mean(diffs)
        residual = [abs(d - offset) for d in diffs]
        rows.append((
            category, offset, max(residual), statistics.mean(residual),
            _spearman([a for a, _ in pairs], [b for _, b in pairs]),
            sum(1 for r in residual if r <= 5), len(residual),
        ))
    return rows


def direction(run: dict) -> tuple[str, str, int, int, float] | None:
    """How one-sided the disagreement is. A near-total sign agreement is calibration."""
    table = means(run)
    providers = sorted({p for cell in table.values() for p in cell})
    if len(providers) != 2:
        return None
    low, high = providers
    diffs = [cell[high] - cell[low] for cell in table.values() if len(cell) == 2]
    positive = sum(1 for d in diffs if d > 0)
    return low, high, positive, len(diffs), statistics.mean(diffs)


def _keyed(findings: list[dict], key: str) -> set:
    if key == "rule+locator":
        return {(_norm(f["rule_id"]), _norm(f["locator"])) for f in findings}
    if key == "locator":
        return {_norm(f["locator"]) for f in findings}
    return {_norm(f.get("evidence", ""))[:80] for f in findings if f.get("evidence")}


def _jaccard(left: set, right: set) -> float | None:
    if not left and not right:
        return None
    return len(left & right) / len(left | right)


def _chance_jaccard(sizes: list[int], universe: int) -> float | None:
    """What two judges score by flagging at random, at the sizes they flagged.

    A resume has 5-9 bullets plus the summary and each judge flags 4-11 of them,
    so raw overlap cannot tell agreement from two judges both marking most of a
    short list. Ratio of expectations: sets of size a and b meet in a*b/N and
    cover a + b - a*b/N.
    """
    if len(sizes) != 2 or universe <= 0:
        return None
    a, b = (min(size, universe) for size in sizes)
    if not a and not b:
        return None
    meet = a * b / universe
    cover = a + b - meet
    return meet / cover if cover else None


def key_table(run: dict, keys: tuple[str, ...]) -> list[tuple]:
    """The same findings compared under different notions of "the same finding"."""
    rows = []
    for key in keys:
        within: list[float] = []
        between: list[float] = []
        chances: list[float] = []
        kappas: list[float] = []
        for resume in scored(run):
            per: dict[str, dict[int, list[dict]]] = defaultdict(dict)
            for judgment in resume["judgments"]:
                per[_provider(judgment["provider"])][judgment["sample"]] = judgment["findings"]
            pooled = {}
            for provider, samples in per.items():
                sets = [_keyed(f, key) for f in samples.values()]
                if len(sets) == 2:
                    score = _jaccard(*sets)
                    if score is not None:
                        within.append(score)
                pooled[provider] = set().union(*sets) if sets else set()
            if len(pooled) == 2:
                score = _jaccard(*pooled.values())
                if score is not None:
                    between.append(score)
                    universe = len(set().union(*pooled.values()))
                    baseline = _chance_jaccard([len(v) for v in pooled.values()], universe)
                    if baseline is not None:
                        chances.append(baseline)
                        if baseline < 1:
                            kappas.append((score - baseline) / (1 - baseline))
        rows.append((key, statistics.mean(within) if within else None,
                     statistics.mean(between) if between else None,
                     statistics.mean(chances) if chances else None,
                     statistics.mean(kappas) if kappas else None))
    return rows


def vocabulary(run: dict) -> tuple[Counter, dict[str, Counter]]:
    """How many names the judges invented for how many findings."""
    overall: Counter = Counter()
    per_provider: dict[str, Counter] = defaultdict(Counter)
    for resume in scored(run):
        for judgment in resume["judgments"]:
            for finding in judgment["findings"]:
                overall[finding["rule_id"]] += 1
                per_provider[_provider(judgment["provider"])][finding["rule_id"]] += 1
    return overall, per_provider


def extract(run: dict) -> dict:
    """The same run with every span of resume text removed.

    Scores, rule ids and locators carry no resume content; `evidence`, `message`,
    `fix` and each category's `why` all quote or paraphrase the document, so they
    come out. Resumes that are not repo fixtures are renamed.
    """
    names = {}
    for resume in run["resumes"]:
        if resume["name"] not in FIXTURES:
            names[resume["name"]] = f"private_resume_{len(names) + 1}"
    out = {
        "meta": dict(run["meta"], redacted=(
            "Derived from a raw agreement run by scripts/baseline_analysis.py "
            "--extract. Quoted resume text, finding messages and category "
            "justifications removed; non-fixture resumes renamed.")),
        "resumes": [],
    }
    for resume in run["resumes"]:
        entry = {
            "name": names.get(resume["name"], resume["name"]),
            "skipped": resume.get("skipped", False),
            "judgments": [
                {
                    "provider": judgment["provider"],
                    "sample": judgment["sample"],
                    "categories": {c: {"score": e["score"]}
                                   for c, e in judgment["categories"].items()},
                    "findings": [{"rule_id": f["rule_id"], "locator": f["locator"],
                                  "severity": f.get("severity", ""),
                                  "source": f.get("source", "")}
                                 for f in judgment["findings"]],
                }
                for judgment in resume["judgments"]
            ],
        }
        out["resumes"].append(entry)
    return out


def report(run: dict) -> str:
    lines = ["", "Baseline decomposition", ""]
    meta = run.get("meta", {})
    lines.append(f"  providers   {', '.join(meta.get('providers', []))}")
    lines.append(f"  samples     {meta.get('samples_per_provider')} per provider")
    lines.append(f"  generated   {meta.get('generated')}")
    if meta.get("redacted"):
        lines.append("  source      redacted extract; evidence-keyed rows unavailable")

    aim = direction(run)
    if aim:
        low, high, positive, total, mean = aim
        lines += ["", "Is the disagreement directional?", ""]
        lines.append(f"  {high} scores above {low} in {positive}/{total} "
                     f"category-resume cells, mean {mean:+.1f} points")
        lines.append("  A near-total sign agreement is calibration, not disagreement "
                     "about resumes.")

    rows = offset_table(run)
    if rows:
        lines += ["", "What survives removing each category's own offset", "",
                  f"  {'category':<30}{'offset':>8}{'resid mean':>12}{'resid max':>11}"
                  f"{'spearman':>10}{'within 5':>10}"]
        for category, offset, worst, mean, rho, ok, n in rows:
            rho_text = "  -  " if rho is None else f"{rho:.2f}"
            lines.append(f"  {category:<30}{offset:>+8.1f}{mean:>12.1f}{worst:>11.1f}"
                         f"{rho_text:>10}{f'{ok}/{n}':>10}")
        residual_mean = statistics.mean(r[3] for r in rows)
        lines.append("")
        lines.append(f"  Offset removed, {residual_mean:.1f} points of disagreement remain "
                     "on average -- still past the 5-point bar.")

    keys = ("rule+locator", "locator") if meta.get("redacted") else (
        "rule+locator", "locator", "evidence")
    lines += ["", "The same findings, under different notions of \"the same finding\"", "",
              f"  {'key':<16}{'within judge':>14}{'between judges':>16}{'chance':>9}{'kappa':>8}"]
    for key, within, between, chance, kappa in key_table(run, keys):
        fmt = lambda v: "  -  " if v is None else f"{v:.2f}"
        signed = "  -  " if kappa is None else f"{kappa:+.2f}"
        lines.append(f"  {key:<16}{fmt(within):>14}{fmt(between):>16}"
                     f"{fmt(chance):>9}{signed:>8}")
    lines.append("")
    lines.append("  Read kappa, not between: a between below its chance line is not "
                 "agreement (ticket 10).")

    overall, per_provider = vocabulary(run)
    lines += ["", "Rule-id vocabulary", ""]
    lines.append(f"  {len(overall)} distinct ids over {sum(overall.values())} findings")
    for provider, counter in sorted(per_provider.items()):
        lines.append(f"    {provider:<12}{len(counter):>4} distinct over "
                     f"{sum(counter.values())} findings")
    if len(per_provider) == 2:
        left, right = (set(c) for c in per_provider.values())
        lines.append(f"    shared by both{len(left & right):>4}")
    lines.append("")
    for rule_id, count in overall.most_common(8):
        lines.append(f"    {count:>3}  {rule_id}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("run", help="a saved agreement run, or a redacted extract")
    parser.add_argument("--extract", metavar="OUT",
                        help="write a redacted copy here instead of reporting")
    args = parser.parse_args()

    path = Path(args.run)
    if not path.exists():
        raise SystemExit(
            f"no such run: {path}\n"
            "Raw runs are gitignored because they quote resumes verbatim. Produce one "
            "with scripts/agreement_harness.py, or point this at a redacted extract.")
    run = load(path)

    if args.extract:
        out = Path(args.extract)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(extract(run), indent=2) + "\n", encoding="utf-8")
        print(f"redacted extract written to {out}")
        return 0

    print(report(run))
    return 0


if __name__ == "__main__":
    sys.exit(main())
