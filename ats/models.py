"""Core data types shared by every stage of the pipeline."""
from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator


class Severity(str, Enum):
    """How much a finding costs. Values are points, read from weights.toml at runtime."""

    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"


class Provenance(str, Enum):
    """Why a rule exists. Heuristic rules are capped at MINOR and can never sink a score."""

    PARSER_MECHANICS = "parser-mechanics"
    JD_DERIVED = "jd-derived"
    RECRUITER_EVIDENCE = "recruiter-evidence"
    HEURISTIC = "heuristic"


class Gate(str, Enum):
    """Which of the two gates a finding belongs to."""

    PARSER = "parser"
    RECRUITER = "recruiter"
    MANAGER = "manager"


class Category(str, Enum):
    """The rubric's axes. Declaration order is report order.

    Five of these were designed by the rubric-grounding map's 04 out of what the JD
    corpus actually asks for, and each has a spec in `ats/criteria/` naming the
    criteria a judge answers and the band those answers buy. The other three are the
    mechanical ones, which that map left alone.

    The five retired here -- `Impact & quantification`, `AI/ML relevance & depth`,
    `Credibility & verifiability`, `Recruiter scan`, `Writing quality` -- were not
    evolved into these. 04 replaced them: their evidence is redistributed by
    `rule-mapping.md` §1, and none of them is a renaming of anything below.
    """

    PARSEABILITY = "Parseability"
    STRUCTURE = "Structure & formatting"
    TITLE = "Title & seniority alignment"
    PRODUCTION_OWNERSHIP = "Production ownership"
    AGENTIC_SYSTEMS = "Agentic systems"
    EVALUATION_RIGOUR = "Evaluation rigour"
    AI_ASSISTED_CODING = "AI-assisted coding fluency"
    RESUME_CRAFT = "Resume craft"


# The four whose weight is document frequency over the JD corpus rather than a number
# somebody chose (04, and the migration map's 02 for the budget they share). Everything
# else in `Category` carries an authored weight, because no posting states it.
DERIVED_CATEGORIES: tuple[Category, ...] = (
    Category.PRODUCTION_OWNERSHIP,
    Category.AGENTIC_SYSTEMS,
    Category.EVALUATION_RIGOUR,
    Category.AI_ASSISTED_CODING,
)

# The five a judge answers criteria for. `Category.PARSEABILITY`, `STRUCTURE` and
# `TITLE` are decided by rules alone and are never put to a model.
JUDGED_CATEGORIES: tuple[Category, ...] = DERIVED_CATEGORIES + (Category.RESUME_CRAFT,)

CATEGORY_GATE: dict[Category, Gate] = {
    Category.PARSEABILITY: Gate.PARSER,
    Category.STRUCTURE: Gate.PARSER,
    Category.TITLE: Gate.RECRUITER,
    # 12 chose RECRUITER for craft and called the choice provisional, expecting this
    # entry to be read by nothing once findings carried their own gate. Nearly: no
    # *finding* reads it -- `Finding` refuses to default a craft finding's gate, since
    # a `scan/*` defect is the six-second read and a `slop/*` defect is not -- but
    # `score._subscore` still reads it to place the category's own score. That is where
    # 12's other finding bites: `_subscore` is called with the SET
    # {RECRUITER, MANAGER}, so craft's value falls in the same bucket either way and
    # only PARSER versus the rest is load-bearing. The entry is required and inert.
    Category.RESUME_CRAFT: Gate.RECRUITER,
    Category.PRODUCTION_OWNERSHIP: Gate.MANAGER,
    Category.AGENTIC_SYSTEMS: Gate.MANAGER,
    Category.EVALUATION_RIGOUR: Gate.MANAGER,
    Category.AI_ASSISTED_CODING: Gate.MANAGER,
}


class Finding(BaseModel):
    """One specific defect: what is wrong, where, and the fix.

    `evidence` is the quoted span from the resume. A finding without evidence is
    dropped before it reaches the report -- an unevidenced claim is not checkable.

    A finding carries **its own gate** and may carry **no category**. The two go
    together, and both come from `rule-mapping.md` §2:

    * `advice_only` findings deduct nothing. They fire, they print their message and
      fix, and they are evidence for no band -- so they must not appear in any
      category's ledger, and giving them a category would put a number beside
      something that cost nothing. `category` is None for them.
    * A finding with no category still has to print somewhere, and `gate` used to be
      derived from the category, so it now stands on its own. That also frees the
      cases where the category's gate was the wrong answer: `Resume craft` holds both
      `scan/*` findings, which a recruiter meets in the first six seconds, and
      `slop/*` findings, which only a manager reading the bullets will care about.

    `gate` defaults from `CATEGORY_GATE` where a category makes it unambiguous.
    `Resume craft` is the one category where it does not, so a finding filed there
    must name its gate.
    """

    rule_id: str
    category: Category | None = None
    gate: Gate | None = None
    # Fires, prints its fix, deducts nothing (rule-mapping.md §2, and 12's two
    # rulings). Never has a category, and never reaches the ledger.
    advice_only: bool = False
    severity: Severity
    message: str
    fix: str
    evidence: str = ""
    locator: str = ""
    provenance: Provenance = Provenance.HEURISTIC
    confidence: str = "high"
    source: str = "deterministic"
    # What this finding cost the composite. Set during scoring so the report and
    # the ledger always quote the same number.
    points: float = 0.0
    # Category-space severity cost, kept only while scoring converts it into the
    # composite-space `points` above.
    _raw_cost: float = 0.0

    @model_validator(mode="after")
    def _resolve_gate(self) -> "Finding":
        """Fill `gate` from the category, and refuse the two shapes that make no sense.

        An advice-only finding with a category would be a cost with nowhere to go; a
        finding with neither a category nor a gate could not be printed at all.
        """
        if self.advice_only and self.category is not None:
            raise ValueError(
                f"{self.rule_id}: an advice-only finding deducts nothing, so it has "
                f"no category -- it needs a gate instead")
        if self.gate is None:
            if self.category is None:
                raise ValueError(f"{self.rule_id}: needs a gate or a category")
            if self.category is Category.RESUME_CRAFT:
                raise ValueError(
                    f"{self.rule_id}: `Resume craft` holds both recruiter-scan and "
                    f"manager-read defects, so a finding there must name its gate")
            self.gate = CATEGORY_GATE[self.category]
        return self


class CriterionAnswer(BaseModel):
    """One binary evidence question, answered by one judge, with what settles it.

    The unit the content pass now returns instead of a number. `met` is what the band
    lookup (`rubric.band_of`) reads; the quote and the place are what makes the answer
    checkable by somebody who disagrees with it.

    `criterion_id` is qualified -- `production-ownership/C1` -- because it is also the
    `rule_id` of any finding this answer places, and a rule id has to name the kind of
    defect across the whole report, not within one category.
    """

    criterion_id: str
    category: Category
    met: bool
    evidence: str = ""
    locator: str = ""
    why: str = ""
    # What to do about it, asked for only when the answer is `no`. It becomes the
    # placed finding's fix, or is dropped with the answer that had nothing to place.
    fix: str = ""


class UnmetCriterion(BaseModel):
    """A criterion answered `no` with nothing to point at (findings-identity.md §3).

    The absence case: nothing in the resume says any work reached production, so there
    is no quote and no place, and `/CONTEXT.md` requires a finding to carry a quote.
    It is not a finding, then -- it is the other object a `no` produces, and it is the
    most important thing the candidate could be told.

    A `no` that *does* have text to point at is a placed `Finding` instead, keyed on
    the same criterion id. A placed finding whose locator does not resolve against the
    parsed resume is demoted to one of these: the reading survives, the fictional
    address does not.
    """

    criterion_id: str
    category: Category
    name: str
    message: str


class JudgedCategory(BaseModel):
    """What the judges' criterion answers make one category worth (06).

    The unit `score.build` blends, replacing the `(mean, low, high)` tuple it read
    when the model authored a number. Every field here is a lookup or a comparison of
    lookups; nothing in it was chosen by a model.

    **The lower band wins.** Each judge is banded from its own answers by
    `rubric.band_of`, and where two judges land on different bands the category takes
    the lower one. Two reasons, both measured in
    `docs/wayfinder/rubric-migration/criterion-scoring.md`:

    * Averaging the two values puts back the model-authored number 04 removed --
      between C's 58 and B's 78 there is no band, so 68 is a number no rubric names.
    * Intersecting the two judges' *answers* -- the most literal reading of "what is
      combined is answers" -- inverts on `Resume craft`, whose band is the count of
      criteria met rather than a ladder of preconditions. Two judges who each met
      three of five, but not the same three, agree on band C and intersect to band D:
      a markdown for a disagreement neither judge reported, on 100 of the 115
      answer-set pairs where craft's judges agree. A rule that holds for four
      categories and inverts on the fifth is not a rule.

    `band` is None only for a run recorded under the pre-05 prompt, where the model
    authored a number and there are no answers to look a band up from. The agreement
    harness builds those so the *before* picture still scores; nothing live does.
    """

    category: Category
    # The band the category scores: the lowest any judge named, and its value.
    value: float
    band: str | None = None
    band_name: str = ""
    # The highest band any judge named, present only when the judges split. `gap` is
    # how many bands apart the two extremes are -- 1 is the smallest disagreement the
    # rubric can express, and the other map calls anything above 1 a failure rather
    # than a spread.
    high_band: str | None = None
    high_band_name: str = ""
    high_value: float | None = None
    gap: int = 0
    # Qualified criterion ids the judges answered differently. A split that does not
    # cross a band boundary leaves `gap` at 0 and still lands here: it is what the
    # category cost in agreement, and the shared lookup absorbed it.
    split_criteria: list[str] = Field(default_factory=list)
    judges: int = 1

    @model_validator(mode="after")
    def _gap_carries_its_other_band(self) -> "JudgedCategory":
        """A gap and the band across it are one fact, so they cannot arrive apart.

        `contested` reads `gap`, and `score.build` blends `high_value` the moment it is
        true. Left unpaired, a `gap` set without a `high_value` is a TypeError inside
        the blend rather than a bad object at the boundary -- and the failure would
        surface as a crashed report, one field away from the numeric constructor in
        `agreement.py` that legitimately sets neither.

        One-directional on purpose: `combine_bands` fills `high_value` for every
        category it bands, so an *uncontested* one carries a `high_value` equal to its
        own value. It is a gap with nothing across it that cannot exist.
        """
        if self.gap > 0 and self.high_value is None:
            raise ValueError(
                f"{self.category.value}: a gap of {self.gap} bands names no band to be "
                f"contested with -- `high_value` is required whenever `gap` is set")
        return self

    @property
    def contested(self) -> bool:
        """Two judges, two bands. The word is the other map's placeholder."""
        return self.gap > 0

    def reads_as(self) -> str:
        """The plain sentence the report prints instead of a numeric range.

        Two numbers tell a candidate less than two readings, and the readings are what
        the bands are for -- `Shipped` and `Shipped and operated` say what the judges
        actually disagreed about, where 41.2-54.4 says only that they did.
        """
        if not self.contested:
            return ""
        split = ", ".join(self.split_criteria)
        return (f"the judges read this differently: {self.band_name}, or "
                f"{self.high_band_name}" + (f" (split on {split})" if split else ""))


class Rewrite(BaseModel):
    """A proposed edit. Never applied automatically -- a human accepts it in a diff."""

    locator: str
    original: str
    rewritten: str
    what_changed: str
    ranking_score: float = 0.0
    audit_score: float = 0.0
    provider: str = ""


class CategoryScore(BaseModel):
    """One category's score, and whether anything actually assessed it.

    `assessed` is false when no channel could speak to the category at all: no judge
    answered it and no rule can deduct from it. `score.build` starts every category's
    deductions at 0.0, so an unassessed category would otherwise sit at a permanent
    100 and carry its full weight into the composite -- manufacturing a result from a
    check that never ran, which is the same thing the unreadable-document path already
    refuses to do. An unassessed category is printed and excluded from the arithmetic.
    """

    category: Category
    score: float
    weight: float
    # The blended value of the lowest and highest band the judges named, present only
    # when they split. `score` is the low one: 06 chose the lower band, so the range
    # is what the reader is shown *beside* the score, never instead of it.
    low: float | None = None
    high: float | None = None
    note: str = ""
    assessed: bool = True
    # Two judges, two bands. `note` says which two, in words.
    contested: bool = False


class LedgerRow(BaseModel):
    """One line of the score derivation. The ledger is the report's signature element."""

    label: str
    points: float
    rule_id: str = ""
    category: Category | None = None


class FindingGroup(BaseModel):
    """All instances of one rule, presented as a single item to fix."""

    lead: Finding
    instances: list[Finding] = Field(default_factory=list)
    total_points: float = 0.0

    @property
    def count(self) -> int:
        return len(self.instances)


class Report(BaseModel):
    composite: float
    grade: str
    parser_subscore: float
    human_subscore: float
    categories: list[CategoryScore] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)
    rewrites: list[Rewrite] = Field(default_factory=list)
    ledger: list[LedgerRow] = Field(default_factory=list)
    partial: bool = False
    notes: list[str] = Field(default_factory=list)
    run_meta: dict[str, Any] = Field(default_factory=dict)

    def by_gate(self, gate: Gate) -> list[Finding]:
        return [f for f in self.findings if f.gate is gate]

    @property
    def top_fixes(self) -> list[Finding]:
        """Five distinct problems, one per rule.

        Deduplicated by rule because five instances of one defect is one thing to
        fix, and the list exists to show breadth of what to work on.
        """
        order = {Severity.CRITICAL: 0, Severity.MAJOR: 1, Severity.MINOR: 2}
        ranked = sorted(self.findings, key=lambda f: (order[f.severity], -f.points))
        seen: set[str] = set()
        out: list[Finding] = []
        for finding in ranked:
            if finding.rule_id in seen:
                continue
            seen.add(finding.rule_id)
            out.append(finding)
            if len(out) == 5:
                break
        return out

    def grouped(self, gate: Gate) -> list["FindingGroup"]:
        """One entry per rule, with its instances attached.

        Twenty-eight separate cards for one repeated defect is noise, not detail:
        it is a single thing to fix, and rendering it twenty-eight times buries
        the other findings. Instances stay attached so nothing is lost.
        """
        order = {Severity.CRITICAL: 0, Severity.MAJOR: 1, Severity.MINOR: 2}
        buckets: dict[str, list[Finding]] = {}
        for f in self.by_gate(gate):
            buckets.setdefault(f.rule_id, []).append(f)
        groups = [
            FindingGroup(
                lead=sorted(items, key=lambda f: -f.points)[0],
                instances=sorted(items, key=lambda f: -f.points),
                total_points=round(sum(i.points for i in items), 1),
            )
            for items in buckets.values()
        ]
        groups.sort(key=lambda g: (order[g.lead.severity], -g.total_points))
        return groups

    @property
    def rule_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for f in self.findings:
            counts[f.rule_id] = counts.get(f.rule_id, 0) + 1
        return counts
