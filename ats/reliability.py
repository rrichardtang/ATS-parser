"""Krippendorff's alpha: agreement that survives the chance correction.

Raw agreement cannot tell a rubric from a coincidence. If nearly every resume
lands in the same place, two judges agree most of the time by landing there too,
and a bar stated as raw distance -- MAP.md's 5 points, or an exact-band match --
is passable by a rubric that taught them nothing. Ticket 08 asked for this beside
the raw numbers for exactly that reason.

Alpha is used rather than a simpler coefficient because it takes what this corpus
actually looks like: any number of raters, missing judgements where a provider
errored, and three levels of measurement -- today's 0-100 numbers are interval,
ticket 05's bands will be ordinal, and unordered labels are nominal.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Iterable


@dataclass
class Alpha:
    """A chance-corrected agreement coefficient, or the reason there isn't one.

    `value` is None rather than 1.0 in the degenerate cases, because those are
    exactly the coincidences this statistic exists to expose. A run where every
    judge named the same band on every resume has no variance to explain, and
    reporting it as perfect agreement would be the false pass ticket 08 warned
    about.
    """

    value: float | None
    units: int
    note: str = ""

    def __str__(self) -> str:
        return "n/a" if self.value is None else f"{self.value:.2f}"


def alpha(
    units: Iterable[list[Any]], level: str = "interval", order: list[str] | None = None
) -> Alpha:
    """Krippendorff's alpha over units x raters, tolerating missing judgements.

    `units` is one list per unit (here: one resume, on one category) holding the
    value each rater gave it. Units judged fewer than twice carry no information
    about agreement and are dropped, which is how a provider that errored on one
    resume costs that resume rather than the whole run.

    `level` picks the difference function: `nominal` for unordered labels,
    `ordinal` for bands (a two-band miss counts for more than a one-band miss),
    `interval` for today's 0-100 numbers. `order` names the band sequence,
    worst-first; without it ordinal has nothing to rank by.
    """
    usable = [list(values) for values in units if len(values) >= 2]
    if not usable:
        return Alpha(None, 0, "no unit was judged twice")

    coincidence: dict[tuple[Any, Any], float] = defaultdict(float)
    for values in usable:
        pairs = len(values) - 1
        for i, first in enumerate(values):
            for j, second in enumerate(values):
                if i != j:
                    coincidence[(first, second)] += 1.0 / pairs

    marginals: dict[Any, float] = defaultdict(float)
    for (value, _other), weight in coincidence.items():
        marginals[value] += weight
    total = sum(marginals.values())

    classes = list(marginals)
    if len(classes) < 2:
        return Alpha(
            None, len(usable),
            "every judgement was the same value, so there is nothing to agree "
            "about -- undefined, not 1.00",
        )

    if level == "ordinal" and order:
        rank = {label: i for i, label in enumerate(order)}
        classes.sort(key=lambda c: (rank.get(c, len(order)), str(c)))
    else:
        # Ordinal ranking falls back to the values' own order, which is what
        # numbers want. Leaving them in the coincidence map's insertion order
        # would silently rank them by whichever judgement arrived first.
        classes.sort()
    position = {value: i for i, value in enumerate(classes)}
    cumulative: list[float] = []
    running = 0.0
    for value in classes:
        running += marginals[value]
        cumulative.append(running)

    def difference(first: Any, second: Any) -> float:
        if level == "nominal":
            return 0.0 if first == second else 1.0
        if level == "interval":
            return (float(first) - float(second)) ** 2
        low, high = sorted((position[first], position[second]))
        span = cumulative[high] - cumulative[low] + marginals[classes[low]]
        return (span - (marginals[classes[low]] + marginals[classes[high]]) / 2.0) ** 2

    observed = sum(w * difference(a, b) for (a, b), w in coincidence.items())
    expected = sum(
        marginals[a] * marginals[b] * difference(a, b)
        for a in classes
        for b in classes
        if a != b
    )
    if expected <= 0:
        return Alpha(None, len(usable), "no expected disagreement to correct against")
    return Alpha(round(1.0 - (total - 1) * observed / expected, 3), len(usable))
