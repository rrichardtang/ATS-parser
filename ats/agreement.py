"""Inter-judge agreement: the instrument the rubric is judged with.

MAP.md's acceptance test is a claim about two judges, not about a resume -- per
category they must land in the same place, and the composite must not move more
than 5 points between them, above 8 being a failure. Nothing in the pipeline can
show that, because every disagreement is folded away before a score is reported:
`content_pass` averages a provider's samples, `combine_scores` averages across
providers, and the report shows the mean.

So this module keeps the samples apart and reports three numbers per category,
which is what ticket 08 asked for instead of one:

  between-judge spread  how far apart two providers land. The thing the
                        acceptance test is actually about.
  within-judge spread   how far apart one provider lands from itself on a rerun.
                        The noise floor the number above has to clear before it
                        means anything -- judges rerun on identical inputs show
                        low intra-rater reliability, so a between-judge spread no
                        larger than this is sampling noise wearing a disagreement's
                        clothes.
  Krippendorff's alpha  chance-corrected. Judges agreeing on the value nearly
                        every resume lands on is a coincidence, not a rubric, and
                        raw agreement cannot tell the two apart.

Ticket 03 settled that the model will name a *band* rather than author a number,
but that is a decision, not yet code: `prompts.CONTENT_SYSTEM` still asks for
0-100. So the channel is read from the reply rather than assumed -- a number, a
band label, or (ticket 05's second experiment, band versus band-plus-a-point-
inside-it) both at once, each with the agreement statistic its scale deserves.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Iterable

from . import config, passes, pipeline
from .extract import extract
from .llm import Provider
from .models import Category, Finding
from .reliability import Alpha, alpha
from .score import build
from .sections import parse

# MAP.md's composite bar, which ticket 03 kept: 5 points between judges passes,
# above 8 fails, and between the two is a pass that wants another look.
COMPOSITE_PASS = 5.0
COMPOSITE_FAIL = 8.0
PASS, LOOK, FAIL = "pass", "look", "FAIL"


def verdict(spread: float) -> str:
    if spread <= COMPOSITE_PASS:
        return PASS
    return LOOK if spread <= COMPOSITE_FAIL else FAIL


# --------------------------------------------------------------------------
# Collecting judgements
# --------------------------------------------------------------------------


@dataclass
class ResumeRun:
    """Every judgement of one resume, unfolded, plus the rules both judges share."""

    name: str
    path: str
    deterministic: list[Finding] = field(default_factory=list)
    judgments: list[passes.ContentJudgment] = field(default_factory=list)
    skipped: str = ""
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "path": self.path,
            "skipped": self.skipped,
            "errors": self.errors,
            "deterministic": [f.model_dump(mode="json") for f in self.deterministic],
            "judgments": [
                {
                    "provider": j.provider,
                    "sample": j.sample,
                    "categories": j.categories,
                    "findings": [f.model_dump(mode="json") for f in j.findings],
                }
                for j in self.judgments
            ],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ResumeRun":
        return cls(
            name=data["name"],
            path=data.get("path", ""),
            deterministic=[Finding.model_validate(f) for f in data.get("deterministic", [])],
            judgments=[
                passes.ContentJudgment(
                    provider=j["provider"],
                    sample=int(j["sample"]),
                    categories=j.get("categories", {}),
                    findings=[Finding.model_validate(f) for f in j.get("findings", [])],
                )
                for j in data.get("judgments", [])
            ],
            skipped=data.get("skipped", ""),
            errors=data.get("errors", []),
        )


@dataclass
class HarnessRun:
    """One sweep of the corpus, saved whole so a rubric change is judged on a diff.

    The raw judgements are kept rather than the tables computed from them: a
    later change to how agreement is measured should be re-runnable against the
    calls already paid for, and "the evidence any rubric change is judged on"
    has to still be there when the next change arrives.
    """

    meta: dict = field(default_factory=dict)
    resumes: list[ResumeRun] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"meta": self.meta, "resumes": [r.to_dict() for r in self.resumes]}

    @classmethod
    def from_dict(cls, data: dict) -> "HarnessRun":
        return cls(
            meta=data.get("meta", {}),
            resumes=[ResumeRun.from_dict(r) for r in data.get("resumes", [])],
        )


def judge_resume(
    providers: list[Provider],
    name: str,
    pdf_path: str,
    samples: int,
    temperature: float,
) -> ResumeRun:
    """Run one resume past every provider `samples` times, keeping the replies apart.

    No job description is passed, on purpose: a posting would move the judgement
    and the corpus is meant to be comparable across resumes and across runs. The
    personal-corpus digest still reaches the prompt, because it reaches every
    real run too.
    """
    doc = extract(pdf_path)
    resume = parse(doc.text)
    findings = pipeline.deterministic(doc, resume, "", pipeline.resolve_target_title(""))
    if not doc.has_text_layer:
        return ResumeRun(
            name, str(pdf_path), findings,
            skipped="no text layer, so the content pass never runs on this document",
        )
    judgments, errors = passes.content_judgments(
        providers, resume, doc.text, "", findings, samples, temperature,
        config.jd_digest(),
    )
    return ResumeRun(name, str(pdf_path), findings, judgments, errors=errors)


def collect(
    providers: list[Provider],
    targets: list[tuple[str, str]],
    samples: int,
    temperature: float,
    notes: list[str] | None = None,
) -> HarnessRun:
    """`targets` is [(name, pdf path)] -- the fixtures, plus the real resume."""
    meta = {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "providers": [p.label for p in providers],
        "samples_per_provider": samples,
        "temperature": temperature,
        "notes": list(notes or []),
    }
    return HarnessRun(
        meta=meta,
        resumes=[
            judge_resume(providers, name, path, samples, temperature)
            for name, path in targets
        ],
    )


def planned_calls(targets: list[tuple[str, str]], providers: int, samples: int) -> int:
    """An upper bound: a resume with no text layer is skipped before any call."""
    return len(targets) * providers * samples


# --------------------------------------------------------------------------
# Reading a judgement: number, band, or both
# --------------------------------------------------------------------------


def numeric_of(entry: dict) -> float | None:
    try:
        return float(entry["score"])
    except (KeyError, TypeError, ValueError):
        return None


def band_of(entry: dict) -> str | None:
    label = entry.get("band")
    return label.strip() if isinstance(label, str) and label.strip() else None


def _per_provider(
    run: ResumeRun, category: str, read: Callable[[dict], Any]
) -> dict[str, list]:
    """provider -> its value for this category, one per sample that supplied one."""
    out: dict[str, list] = defaultdict(list)
    for judgment in run.judgments:
        entry = judgment.categories.get(category)
        if entry is None:
            continue
        value = read(entry)
        if value is not None:
            out[judgment.provider].append(value)
    return dict(out)


def _mean(values: Iterable[float]) -> float:
    values = list(values)
    return sum(values) / len(values) if values else 0.0


def _spread(values: Iterable[float]) -> float:
    values = list(values)
    return max(values) - min(values) if len(values) > 1 else 0.0


# --------------------------------------------------------------------------
# What a judgement would put on the report
# --------------------------------------------------------------------------


@dataclass
class Scored:
    """One judgement run through the real scoring code, not a reimplementation.

    Two composites, because ticket 03 moved the model's findings out of the
    deduction channel and that change is not in the code yet:

      as_built     what the tool reports today -- the model's number blended into
                   each category AND its findings deducting on top, the double
                   count 03 closed.
      no_deduct    the same judgement with model findings carrying no cost, which
                   is the composite every rubric change from here is judged on.

    Showing both makes the size of that double count a measurement rather than an
    argument.
    """

    provider: str
    as_built: float
    no_deduct: float
    categories: dict[str, float]
    capped: bool = False


def score_judgment(run: ResumeRun, judgment: passes.ContentJudgment) -> Scored | None:
    """None when the judgement carried no number -- a band has no value until 05."""
    values: dict[Category, tuple[float, float, float]] = {}
    for name, entry in judgment.categories.items():
        value = numeric_of(entry)
        if value is not None:
            values[Category(name)] = (value, value, value)
    if not values:
        return None
    as_built = build(run.deterministic + judgment.findings, llm_categories=values)
    no_deduct = build(run.deterministic, llm_categories=values)
    return Scored(
        provider=judgment.provider,
        as_built=as_built.composite,
        no_deduct=no_deduct.composite,
        categories={c.category.value: c.score for c in as_built.categories},
        capped=any(row.rule_id == "score/cap" for row in as_built.ledger),
    )


# --------------------------------------------------------------------------
# The tables
# --------------------------------------------------------------------------


@dataclass
class NumericAgreement:
    """`None` where a spread was never measured, which is not the same as 0.0.

    A category only one judge scored has no between-judge spread, and a run of one
    sample per provider has no within-judge spread. Reporting either as zero reads
    as perfect agreement -- and would contradict the alpha on the same row, which
    already says `n/a`.
    """

    category: str
    resumes: int
    between_mean: float | None
    between_max: float | None
    within_mean: float | None
    within_max: float | None
    alpha: Alpha
    over_bar: int


@dataclass
class BandAgreement:
    category: str
    resumes: int
    exact: int
    adjacent: int
    far: int
    unstable: int
    alpha: Alpha

    @property
    def verdict(self) -> str:
        """MAP.md's restated per-category test, applied per resume then totalled.

        One wobble across the corpus is a pass that wants another look; more than
        one, or any non-adjacent miss, is a failure of the rubric.

        A judge that named two bands for the same resume on a rerun counts as a
        wobble too: it has failed the same test from the other direction, and
        leaving it out would let a category read `pass` on a rubric no judge can
        apply twice running.
        """
        wobbles = self.adjacent + self.unstable
        if self.far or wobbles > 1:
            return FAIL
        return LOOK if wobbles else PASS


@dataclass
class CompositeRow:
    resume: str
    as_built: dict[str, float]
    no_deduct: dict[str, float]
    # A composite held down by the fraud or unreadable cap is the same number
    # whatever the judges said, so its spread is not evidence they agreed.
    capped: bool = False

    @property
    def comparable(self) -> bool:
        """False when only one judge scored this resume -- the other errored, or
        only one key was supplied. Its spread is then 0 by construction, which is
        the absence of a measurement rather than agreement, so nothing downstream
        may read it as a pass."""
        return len(self.as_built) > 1

    @property
    def spread_as_built(self) -> float:
        return _spread(self.as_built.values())

    @property
    def spread_no_deduct(self) -> float:
        return _spread(self.no_deduct.values())


FINDING_KEYS = ("kind+locator", "locator", "evidence")


def _norm(text: str) -> str:
    return " ".join((text or "").split()).lower()


def _finding_key(finding: Finding, key: str):
    """One finding reduced to whatever "the same finding" is taken to mean."""
    if key == "kind+locator":
        return (_norm(finding.rule_id), _norm(finding.locator))
    if key == "locator":
        return _norm(finding.locator)
    return _norm(finding.evidence)[:80] or None


@dataclass
class FindingsRow:
    """Findings agreement under one notion of "the same finding".

    Ticket 10: the choice of key moved this number 17x on the baseline run, so
    the harness reports every candidate rather than picking one silently.
    `kind+locator` is the key of record -- two judges naming the same defect in
    the same place have agreed even if they phrased it differently, and
    `rule_id` is the kind, which is what the report groups by. It is only
    meaningful once `rule_id` comes from a closed list; while the model invents
    the name, this row reads near zero for that reason and not because the
    judges disagree.

    `chance` is what two judges would score by flagging at random, at the sizes
    they actually flagged, from the pool of keys actually in play. `kappa` is
    the overlap corrected for it. Raw overlap alone cannot tell agreement from a
    short list both judges mark most of: on the baseline run, locator overlap of
    0.51 sat *below* its 0.59 chance line.
    """

    resume: str
    key: str
    keys: int
    between: float | None
    chance: float | None
    kappa: float | None
    within: dict[str, float]


@dataclass
class AgreementReport:
    meta: dict
    providers: list[str]
    numeric: list[NumericAgreement] = field(default_factory=list)
    bands: list[BandAgreement] = field(default_factory=list)
    composites: list[CompositeRow] = field(default_factory=list)
    findings: list[FindingsRow] = field(default_factory=list)
    skipped: list[tuple[str, str]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def _jaccard(left: set, right: set) -> float | None:
    union = left | right
    return len(left & right) / len(union) if union else None


def _chance_jaccard(sizes: list[int], universe: int) -> float | None:
    """Expected overlap if each judge flagged at random, at the size it flagged.

    Ratio of expectations over a universe of `universe` distinct keys: two sets
    of size a and b meet in a*b/N on average and cover a + b - a*b/N. A judge
    that flags most of a short list overlaps another one heavily for no reason
    at all, and this is the line that says so.
    """
    if len(sizes) != 2 or universe <= 0:
        return None
    a, b = (min(s, universe) for s in sizes)
    if not a and not b:
        return None
    meet = a * b / universe
    cover = a + b - meet
    return meet / cover if cover else None


def _mean_jaccard(groups: list[set]) -> float | None:
    """Mean overlap over every pair. None when there is no pair, or nothing found."""
    pairs = [
        _jaccard(groups[i], groups[j])
        for i in range(len(groups))
        for j in range(i + 1, len(groups))
    ]
    scored = [p for p in pairs if p is not None]
    return _mean(scored) if scored else None


def analyse(run: HarnessRun, band_order: list[str] | None = None) -> AgreementReport:
    live = [r for r in run.resumes if not r.skipped and r.judgments]
    providers = sorted({j.provider for r in live for j in r.judgments})
    notes = list(run.meta.get("notes") or [])
    report = AgreementReport(
        meta=run.meta,
        providers=providers,
        skipped=[(r.name, r.skipped) for r in run.resumes if r.skipped],
        notes=notes,
    )
    if not live:
        notes.append("No resume produced a judgement, so there is nothing to compare.")
        return report

    if len(providers) < 2:
        notes.append(
            f"One provider ({providers[0] if providers else 'none'}). Between-judge "
            "agreement is the acceptance test and cannot be measured with one judge; "
            "only the within-judge noise floor below is real."
        )

    scored: dict[str, list[Scored]] = {
        r.name: [s for s in (score_judgment(r, j) for j in r.judgments) if s]
        for r in live
    }

    report.numeric = _numeric_tables(live, scored)
    report.bands = _band_tables(live, band_order)
    report.composites = _composite_rows(live, scored)
    report.findings = _findings_rows(live)

    if report.bands and not band_order:
        notes.append(
            "Band labels were returned but no band order was declared (--bands), so "
            "adjacency is unknown: every miss is counted non-adjacent and alpha falls "
            "back to nominal, which under-reports agreement."
        )
    undefined = {
        row.alpha.note
        for row in (*report.numeric, *report.bands)
        if row.alpha.value is None and row.alpha.note
    }
    notes.extend(sorted(f"alpha: {note}" for note in undefined))

    # A sweep that lost calls has fewer judges than it looks like it has, so the
    # failures belong beside the numbers rather than in the terminal scrollback.
    failures: dict[str, int] = defaultdict(int)
    for resume in run.resumes:
        for error in resume.errors:
            failures[error] += 1
    notes.extend(
        f"{count} call(s) failed: {error}" for error, count in sorted(failures.items())
    )
    return report


def _categories(live: list[ResumeRun], read: Callable[[dict], Any]) -> list[str]:
    """Every category some judge answered on this channel, numeric or band."""
    return sorted({
        name
        for run in live
        for judgment in run.judgments
        for name, entry in judgment.categories.items()
        if read(entry) is not None
    })


def _numeric_tables(
    live: list[ResumeRun], scored: dict[str, list[Scored]]
) -> list[NumericAgreement]:
    categories = _categories(live, numeric_of)

    tables = []
    for category in categories:
        between: list[float] = []
        within: list[float] = []
        units: list[list[float]] = []
        over_bar = 0
        resumes = 0

        for run in live:
            by_provider = _per_provider(run, category, numeric_of)
            if not by_provider:
                continue
            resumes += 1
            means = [_mean(values) for values in by_provider.values()]
            within += [_spread(values) for values in by_provider.values() if len(values) > 1]
            if len(means) > 1:
                between.append(_spread(means))
            units.append(means)

            # The bar was always stated against the *blended* category score, not
            # the model's raw number: the model's disagreement reaches the report
            # scaled by (1 - rule_share), which differs 2x between categories.
            # Only the judges that scored THIS category: `Scored.categories` holds
            # every category the report carries, so a provider that omitted one
            # still has a rule-only blended value there. Including it would compare
            # a judge with a number against a judge without one.
            blended: dict[str, list[float]] = defaultdict(list)
            for entry in scored.get(run.name, []):
                if entry.provider in by_provider and category in entry.categories:
                    blended[entry.provider].append(entry.categories[category])
            if len(blended) > 1 and _spread([_mean(v) for v in blended.values()]) > COMPOSITE_PASS:
                over_bar += 1

        tables.append(NumericAgreement(
            category=category,
            resumes=resumes,
            between_mean=round(_mean(between), 1) if between else None,
            between_max=round(max(between), 1) if between else None,
            within_mean=round(_mean(within), 1) if within else None,
            within_max=round(max(within), 1) if within else None,
            alpha=alpha(units, level="interval"),
            over_bar=over_bar,
        ))
    return tables


def _band_tables(live: list[ResumeRun], order: list[str] | None) -> list[BandAgreement]:
    categories = _categories(live, band_of)
    rank = {label: i for i, label in enumerate(order or [])}

    tables = []
    for category in categories:
        exact = adjacent = far = unstable = resumes = 0
        units: list[list[str]] = []

        for run in live:
            by_provider = _per_provider(run, category, band_of)
            if not by_provider:
                continue
            # A provider that names two different bands for the same resume has
            # not stated a judgement to compare, so it is excluded rather than
            # arbitrarily reduced to one of them -- and counted, because that
            # instability is itself a rubric failure.
            stable = {p: v[0] for p, v in by_provider.items() if len(set(v)) == 1}
            if len(stable) < len(by_provider):
                resumes += 1
                unstable += 1
                continue
            if len(stable) < 2:
                # One judge's band matches itself by construction. Counting that
                # as agreement is the same false pass as printing a zero spread
                # for a lone judge.
                continue
            resumes += 1
            units.append(list(stable.values()))
            labels = sorted(set(stable.values()))
            ranks = [rank[label] for label in labels if label in rank]
            if len(labels) <= 1:
                exact += 1
            elif len(labels) == 2 and len(ranks) == 2 and abs(ranks[0] - ranks[1]) == 1:
                adjacent += 1
            else:
                # Two bands the declared order does not place are not "far" for a
                # measured reason, but counting them as adjacent would be a guess
                # in the rubric's favour.
                far += 1

        tables.append(BandAgreement(
            category=category,
            resumes=resumes,
            exact=exact,
            adjacent=adjacent,
            far=far,
            unstable=unstable,
            alpha=alpha(units, level="ordinal" if order else "nominal", order=order),
        ))
    return tables


def _composite_rows(
    live: list[ResumeRun], scored: dict[str, list[Scored]]
) -> list[CompositeRow]:
    rows = []
    for run in live:
        entries = scored.get(run.name) or []
        if not entries:
            continue
        as_built: dict[str, list[float]] = defaultdict(list)
        no_deduct: dict[str, list[float]] = defaultdict(list)
        for entry in entries:
            as_built[entry.provider].append(entry.as_built)
            no_deduct[entry.provider].append(entry.no_deduct)
        rows.append(CompositeRow(
            resume=run.name,
            as_built={p: round(_mean(v), 1) for p, v in as_built.items()},
            no_deduct={p: round(_mean(v), 1) for p, v in no_deduct.items()},
            capped=all(e.capped for e in entries),
        ))
    return rows


def _findings_rows(live: list[ResumeRun]) -> list[FindingsRow]:
    rows = []
    for run in live:
        for key in FINDING_KEYS:
            by_provider: dict[str, list[set]] = defaultdict(list)
            for judgment in run.judgments:
                by_provider[judgment.provider].append(
                    {k for k in (_finding_key(f, key) for f in judgment.findings)
                     if k is not None}
                )
            pooled = {p: set().union(*samples) for p, samples in by_provider.items()}
            between = _mean_jaccard(list(pooled.values()))
            universe = len(set().union(*pooled.values())) if pooled else 0
            chance = _chance_jaccard([len(v) for v in pooled.values()], universe)
            kappa = None
            if between is not None and chance is not None and chance < 1:
                kappa = (between - chance) / (1 - chance)
            within = {}
            for provider, samples in by_provider.items():
                overlap = _mean_jaccard(samples)
                if overlap is not None:
                    within[provider] = round(overlap, 2)
            rows.append(FindingsRow(
                resume=run.name,
                key=key,
                keys=universe,
                between=None if between is None else round(between, 2),
                chance=None if chance is None else round(chance, 2),
                kappa=None if kappa is None else round(kappa, 2),
                within=within,
            ))
    return rows
