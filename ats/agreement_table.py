"""The harness's output: three tables and the caveats that keep them honest.

This is the artifact ticket 06 exists to produce -- "the evidence any rubric
change is judged on" -- so what it refuses to print matters as much as what it
prints. A between-judge spread is withheld when there is only one judge, a
composite pinned by a cap is marked rather than counted as agreement, and an
alpha that is undefined says so instead of reading as a perfect score.

The tables quote no resume text, which is what makes them the part of a run that
can be pasted into a ticket; the raw judgements they come from cannot.
"""
from __future__ import annotations

from collections import defaultdict

from .agreement import AgreementReport, COMPOSITE_FAIL, COMPOSITE_PASS, FAIL, LOOK, PASS, verdict


def _table(headers: list[str], rows: list[list[str]]) -> list[str]:
    """First column left-aligned, the rest right -- numbers read down a column."""
    if not rows:
        return []
    widths = [
        max([len(headers[i])] + [len(row[i]) for row in rows])
        for i in range(len(headers))
    ]

    def line(cells: list[str]) -> str:
        parts = [cells[0].ljust(widths[0])]
        parts += [cells[i].rjust(widths[i]) for i in range(1, len(cells))]
        return "  ".join(parts).rstrip()

    return [line(headers), "-" * (sum(widths) + 2 * (len(widths) - 1))] + [
        line(row) for row in rows
    ]


def _num(value: float | None) -> str:
    """`-` for a spread that was never measured. Printing 0.0 there would read as
    perfect agreement, which is the opposite of what an absent measurement means."""
    return "-" if value is None else f"{value:.1f}"


def _judged_line(report: AgreementReport) -> list[str]:
    """Configured is not the same as judged: a provider can error out of a sweep."""
    configured = report.meta.get("providers") or []
    if len(report.providers) >= len(configured):
        return []
    return [f"  judged by   {', '.join(report.providers) or 'nobody'} -- the rest "
            "returned nothing for any resume"]


def render(report: AgreementReport) -> str:
    meta = report.meta
    out: list[str] = [
        "Inter-judge agreement",
        f"  providers   {', '.join(meta.get('providers') or ['none'])}",
        *_judged_line(report),
        f"  sampling    {meta.get('samples_per_provider', '?')} samples per provider, "
        f"temperature {meta.get('temperature', '?')}",
        f"  generated   {meta.get('generated', 'unknown')}",
        "",
    ]

    if report.numeric:
        out += [
            "Per-category agreement, in the model's own 0-100 points",
            "",
        ]
        out += _table(
            ["category", "n", "between", "(max)", "within", "(max)", "alpha", "over 5"],
            [
                [
                    row.category, str(row.resumes),
                    _num(row.between_mean), _num(row.between_max),
                    _num(row.within_mean), _num(row.within_max),
                    str(row.alpha), str(row.over_bar),
                ]
                for row in report.numeric
            ],
        )
        out += [
            "",
            "  between  spread between providers        within  one provider against itself",
            "  alpha    Krippendorff, interval          over 5  resumes past 5 blended points",
            "",
        ]

    if report.bands:
        out += ["Per-category band agreement", ""]
        out += _table(
            ["category", "n", "exact", "adjacent", "far", "unstable", "alpha", "verdict"],
            [
                [
                    row.category, str(row.resumes), str(row.exact), str(row.adjacent),
                    str(row.far), str(row.unstable), str(row.alpha), row.verdict,
                ]
                for row in report.bands
            ],
        )
        out += [
            "",
            "  exact/adjacent/far  how far apart the two judges' bands were",
            "  unstable            one provider named two bands for the same resume",
            "",
        ]

    if report.composites:
        out += [f"Composite spread between judges (pass <= {COMPOSITE_PASS:.0f}, "
                f"FAIL > {COMPOSITE_FAIL:.0f})", ""]
        out += _table(
            ["resume", "as built", "verdict", "no deduct", "verdict"],
            [
                [
                    row.resume + (" *" if row.capped else ""),
                    *([f"{row.spread_as_built:.1f}", verdict(row.spread_as_built),
                       f"{row.spread_no_deduct:.1f}", verdict(row.spread_no_deduct)]
                      if row.comparable else ["-", "-", "-", "-"]),
                ]
                for row in report.composites
            ],
        )
        tally = defaultdict(int)
        for row in report.composites:
            if row.comparable:
                tally[verdict(row.spread_no_deduct)] += 1
        out += [
            "",
            "  as built   today's code: the model's number blended in AND its findings deducting",
            "  no deduct  ticket 03: model findings are evidence, not a deduction",
            f"  no-deduct tally: {tally[PASS]} pass, {tally[LOOK]} look, {tally[FAIL]} FAIL",
        ]
        if any(row.capped for row in report.composites):
            out.append(
                "  *  composite pinned by a cap (fraud, or nothing readable), so it "
                "is the same\n     number whatever the judges said -- that row's "
                "spread is not evidence of agreement"
            )
        out.append("")
        out += ["Composite by judge (as built)", ""]
        out += _table(
            ["resume", *report.providers],
            [
                [row.resume] + [
                    f"{row.as_built[p]:.1f}" if p in row.as_built else "-"
                    for p in report.providers
                ]
                for row in report.composites
            ],
        )
        out += [""]

    if report.findings:
        out += ["Findings agreement, under each notion of \"the same finding\"", ""]
        out += _table(
            ["resume", "key", "keys", "between", "chance", "kappa",
             *[f"within {p}" for p in report.providers]],
            [
                [
                    row.resume, row.key, str(row.keys),
                    "-" if row.between is None else f"{row.between:.2f}",
                    "-" if row.chance is None else f"{row.chance:.2f}",
                    "-" if row.kappa is None else f"{row.kappa:+.2f}",
                    *[
                        f"{row.within[p]:.2f}" if p in row.within else "-"
                        for p in report.providers
                    ],
                ]
                for row in report.findings
            ],
        )
        out += [
            "",
            "  Jaccard overlap; 1.00 means the same defects in the same places.",
            "  kind+locator is the key of record and reads near zero while the model",
            "  invents rule ids. Read kappa, not between: chance is what two judges",
            "  score by flagging at random from the same short list, and a between",
            "  below its chance line is not agreement.",
            "",
        ]

    if report.skipped:
        out += ["Skipped", ""]
        out += [f"  {name}: {why}" for name, why in report.skipped]
        out += [""]

    if report.notes:
        out += ["Notes", ""]
        out += [f"  - {note}" for note in report.notes]
        out += [""]

    return "\n".join(out)
