"""The three LLM passes and their ensembling.

Pass 1 and 2 are independent and run concurrently. Pass 3 depends on both, so a
rewrite fixes content defects and slop patterns in one edit instead of trading one
for the other.

Every pass degrades on its own: if one fails, the rest of the report still renders.
"""
from __future__ import annotations

import functools
import logging
from dataclasses import dataclass, field

from . import ensemble, prompts, rubric
from .llm import LLMError, Provider, call
from .models import (
    JUDGED_CATEGORIES,
    Category,
    CriterionAnswer,
    Finding,
    Gate,
    Provenance,
    Rewrite,
    Severity,
    UnmetCriterion,
)
from .sections import Resume

log = logging.getLogger("ats.passes")

MAX_REWRITE_TARGETS = 6

# Only the categories a judge is actually asked about. `Parseability`, `Structure` and
# `Title` are decided by rules alone, so a model naming one of them is answering a
# question nobody put to it -- built over the whole enum, this map would resolve that
# name and hand it to `score.build` to be blended. (`score.build` drops it too; both
# halves matter, because this one also decides where a *finding* files.)
CATEGORY_BY_NAME = {c.value.lower(): c for c in JUDGED_CATEGORIES}


def _rule_id(prefix: str, pattern: str | None, fallback: str) -> str:
    """`<prefix>/<the defect the model named>`.

    A rule id is what the report groups and the ledger totals by, so it has to
    name the KIND of defect. A single id shared by every finding of a pass makes
    unrelated defects one card titled after whichever scored highest.
    """
    slug = (pattern or "").strip().lower().replace(" ", "-")[:40].strip("-")
    return f"{prefix}/{slug or fallback}"


def _category(name: str) -> Category | None:
    return CATEGORY_BY_NAME.get((name or "").strip().lower())


@functools.lru_cache(maxsize=1)
def criteria_index() -> dict[Category, tuple[str, dict[str, dict]]]:
    """Category -> (spec slug, {criterion id: criterion}), from the specs themselves.

    The closed vocabulary a content reply is checked against. It is the rubric's own
    list rather than a copy of it, so a criterion the prompt asks about and a criterion
    the band lookup reads are the same criterion by construction.
    """
    return {
        Category(spec["category"]): (
            spec["slug"], {c["id"]: c for c in spec["criteria"]}
        )
        for spec in rubric.load_specs()
    }


YES = {"yes", "true", "y", "met"}
NO = {"no", "false", "n", "unmet"}


def _met(value) -> bool | None:
    """None when the reply did not actually answer.

    An abstention and a `no` are not the same thing -- `rubric.band_of` refuses an
    incomplete answer set rather than banding one -- so an unreadable answer is
    dropped instead of being read as the absence of evidence.
    """
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().lower()
    if text in YES:
        return True
    if text in NO:
        return False
    return None


def criterion_answers(categories: dict) -> list[CriterionAnswer]:
    """The criterion answers in one reply, checked against the specs.

    Everything the specs do not contain is dropped, exactly as an unevidenced finding
    is dropped: a category nobody asked about (`_category`), a criterion id that does
    not exist, and an answer that is neither yes nor no. A repeated id keeps the first
    answer -- two answers to one question is not a second opinion, it is a malformed
    reply.
    """
    index = criteria_index()
    answers: list[CriterionAnswer] = []
    seen: set[str] = set()
    for name, entry in (categories or {}).items():
        category = _category(name)
        if category is None or not isinstance(entry, dict):
            continue
        slug, criteria = index[category]
        for item in entry.get("criteria") or []:
            if not isinstance(item, dict):
                continue
            cid = str(item.get("id") or "").strip().upper()
            if cid not in criteria:
                continue
            met = _met(item.get("answer"))
            if met is None:
                continue
            qualified = f"{slug}/{cid}"
            if qualified in seen:
                continue
            seen.add(qualified)
            answers.append(CriterionAnswer(
                criterion_id=qualified,
                category=category,
                met=met,
                evidence=(item.get("evidence") or "").strip()[:200],
                locator=(item.get("locator") or "").strip()[:40],
                why=(item.get("why") or "").strip()[:200],
                fix=(item.get("fix") or "").strip()[:200],
            ))
    return answers


def resolvable_locators(resume: Resume) -> set[str]:
    """The places a criterion answer may name: real bullets, plus the summary.

    The rewrite pass already resolved locators this way before spending a call on
    one. Ticket 05 moves that resolution earlier and applies it to every answer.
    """
    places = {locator for locator, text in resume.bullets if text}
    if resume.summary:
        places.add("summary")
    return places


def place(
    answers: list[CriterionAnswer], resume: Resume, provider_name: str,
) -> tuple[list[Finding], list[UnmetCriterion]]:
    """Split the `no` answers into the two objects findings-identity.md §3 defines.

    A `no` with a quote in a place that resolves is a **placed finding**, keyed on the
    criterion id. Anything else a `no` produced -- no quote, no locator, or a locator
    that names nothing in the parsed resume -- is an **unmet criterion**, which is the
    absence the band lookup reads and the report leads with.

    A `yes` produces neither. Its quote is the evidence that settles the criterion and
    it travels on the answer; rendering it as a defect with a fix would be the report
    telling somebody to repair the thing they did right.
    """
    places = resolvable_locators(resume)
    index = criteria_index()
    findings: list[Finding] = []
    unmet: list[UnmetCriterion] = []
    for answer in answers:
        if answer.met:
            continue
        _slug, criteria = index[answer.category]
        criterion = criteria[answer.criterion_id.split("/", 1)[1]]
        if answer.evidence and answer.locator in places:
            findings.append(Finding(
                rule_id=answer.criterion_id,
                category=answer.category,
                # The model reads bullets, not the six-second scan, so a content
                # finding is a manager-read defect wherever it files. `Resume craft`
                # is the category that cannot default its gate, and this is the
                # answer for the findings it holds from here.
                gate=Gate.MANAGER,
                severity=Severity.MAJOR,
                message=(answer.why or criterion["no_looks_like"])[:200],
                fix=answer.fix,
                evidence=answer.evidence,
                locator=answer.locator,
                provenance=Provenance.HEURISTIC,
                source=f"llm:{provider_name}",
            ))
        else:
            unmet.append(UnmetCriterion(
                criterion_id=answer.criterion_id,
                category=answer.category,
                name=criterion["name"],
                message=(answer.why or criterion["no_looks_like"])[:200],
            ))
    return findings, unmet


def withholding_reason(resume: Resume) -> str:
    """Why the judged categories cannot be judged on this document, or "".

    05's rule, and it is not optional: every criterion asks about a bullet inside a
    role, so a document whose roles did not survive extraction has its judged
    categories **withheld** -- not guessed, and not zeroed. The parser gate has
    already found and charged for that defect; scoring it again charges one fault
    twice. `two_column`, `hidden_text` and `scanned` are the documents that exercise
    it.
    """
    if not resume.roles:
        return ("no roles survived extraction, so there are no bullets for a "
                "criterion to be about")
    if not resume.bullets:
        return ("roles parsed but carry no bullets, so there is nothing for a "
                "criterion to be about")
    return ""


@dataclass
class ContentJudgment:
    """One provider's one sample of the content pass, before anything is folded.

    `categories` holds the model's raw entry per category -- `{"criteria": [...]}`
    since 05 -- rather than anything parsed, so a caller that cares about *what* the
    model authored does not have to reconstruct it, and a run recorded before 05
    (which carries `{"score": 62, "why": ...}`) still loads and still measures.

    The validated projection of that raw entry is `criterion_answers(j.categories)`,
    derived on demand rather than stored: it needs nothing but the specs. `unmet` is
    stored, because splitting a `no` into an unmet criterion or a placed finding
    needs the parsed resume, which a saved run does not carry.

    Kept per-sample because sampling noise and genuine provider disagreement are
    only separable while the samples are still apart. content_pass folds the report
    channel -- one card per (criterion, place), one unmet criterion per criterion --
    and by the time it reaches the report every disagreement that produced it is
    gone. ats/agreement.py is the reason the unfolded form exists, and since 05 so
    is the scoring channel: 06 decides what two judges splitting on a criterion buys,
    and it cannot decide it on answers this class has already merged.
    """

    provider: str
    sample: int
    categories: dict[str, dict]
    findings: list[Finding]
    unmet: list[UnmetCriterion] = field(default_factory=list)


def content_judgments(
    providers: list[Provider],
    resume: Resume,
    full_text: str,
    jd_text: str,
    deterministic: list[Finding],
    samples: int,
    temperature: float,
    digest: dict | None = None,
) -> tuple[list[ContentJudgment], list[str]]:
    """Every (provider, sample) reply to the content prompt, parsed but not combined."""
    summary = [f"{f.rule_id}: {f.message}" for f in deterministic]
    user = prompts.content_user(resume, full_text, jd_text, summary, digest)

    jobs = []
    for provider in providers:
        for index in range(samples):
            temp = 0.0 if samples == 1 else temperature
            jobs.append(
                lambda p=provider, i=index, t=temp: (
                    p.name, i, call(p, prompts.content_system(), user, t)
                )
            )

    raw, errors = ensemble.gather(jobs)

    judgments: list[ContentJudgment] = []
    for provider_name, index, payload in raw:
        categories: dict[str, dict] = {}
        for name, entry in (payload.get("categories") or {}).items():
            category = _category(name)
            if category and isinstance(entry, dict):
                categories[category.value] = entry

        # The model has no findings vocabulary of its own any more: a finding is the
        # evidence for one criterion and its id is the criterion's, so both objects a
        # reply produces come out of the answers rather than out of a `findings` array
        # the model would have had to name the defects in.
        findings, unmet = place(
            criterion_answers(categories), resume, provider_name
        )
        judgments.append(ContentJudgment(provider_name, index, categories, findings, unmet))

    return judgments, errors


def content_pass(
    providers: list[Provider],
    resume: Resume,
    full_text: str,
    jd_text: str,
    deterministic: list[Finding],
    samples: int,
    temperature: float,
    digest: dict | None = None,
) -> ensemble.PassResult:
    """The criterion answers behind every judged category, and what they place.

    Two channels come out of here and they fold differently:

    * the **report** channel -- placed findings and unmet criteria -- is unioned
      across judgements here, keyed on `(rule_id, locator)` and on the criterion id
      respectively, exactly as findings were unioned before 05.
    * the **scoring** channel -- the answers themselves -- is deliberately *not*
      folded. Two judges answering the same five questions differently is a criterion
      split, not a spread of numbers, and what to do about it is ticket 06's decision.
      The unfolded answers stay on each `ContentJudgment`, which is where 06 and
      `ats/agreement.py` read them.
    """
    withheld = withholding_reason(resume)
    if withheld:
        return ensemble.PassResult(
            meta={
                "withheld": [c.value for c in JUDGED_CATEGORIES],
                "withheld_reason": withheld,
                "samples_per_provider": samples,
            },
        )

    judgments, errors = content_judgments(
        providers, resume, full_text, jd_text, deterministic, samples,
        temperature, digest,
    )

    findings: list[Finding] = []
    seen: set[tuple[str, str]] = set()
    unmet: list[UnmetCriterion] = []
    seen_unmet: set[str] = set()
    answered: set[str] = set()

    for judgment in judgments:
        answered.update(a.criterion_id for a in criterion_answers(judgment.categories))
        for finding in judgment.findings:
            # 10's key of record: the kind of defect and the place it is in. Both
            # halves are closed now -- the id comes from the specs and the locator
            # resolved against the parsed resume -- so two judges reporting one defect
            # collide here instead of arriving as two cards worded differently.
            key = (finding.rule_id, finding.locator)
            if key in seen:
                continue
            seen.add(key)
            findings.append(finding)
        for criterion in judgment.unmet:
            if criterion.criterion_id in seen_unmet:
                continue
            seen_unmet.add(criterion.criterion_id)
            unmet.append(criterion)

    return ensemble.PassResult(
        data=findings,
        providers_used=sorted({j.provider for j in judgments}),
        errors=errors,
        meta={
            "providers": sorted({j.provider for j in judgments}),
            "unmet": [c.model_dump(mode="json") for c in unmet],
            "criteria_answered": len(answered),
            "criteria_asked": sum(len(c) for _slug, c in criteria_index().values()),
            "samples_per_provider": samples,
        },
    )


def slop_pass(
    providers: list[Provider],
    resume: Resume,
    caught: list[str],
    samples: int,
    vote_k: int,
    temperature: float,
) -> ensemble.PassResult:
    """Named slop patterns beyond regex reach. Never scores AI-likelihood."""
    user = prompts.slop_user(resume, caught)

    jobs = []
    for provider in providers:
        for _ in range(samples):
            temp = 0.0 if samples == 1 else temperature
            jobs.append(
                lambda p=provider, t=temp: (p.name, call(p, prompts.SLOP_SYSTEM, user, t))
            )

    raw, errors = ensemble.gather(jobs)
    per_provider: dict[str, list[list[dict]]] = {}
    for provider_name, payload in raw:
        items = [i for i in (payload.get("findings") or []) if isinstance(i, dict)]
        per_provider.setdefault(provider_name, []).append(items)

    combined, meta = ensemble.combine_slop(per_provider, vote_k) if per_provider else ([], {})
    resume_text = " ".join([resume.summary] + [b for _, b in resume.bullets])
    combined = ensemble.filter_slop(combined, resume_text)

    locator_by_text = {
        " ".join(text.split()).lower(): loc for loc, text in resume.bullets
    }

    findings = []
    for item in combined:
        quote = item["quoted_line"].strip()
        locator = "summary"
        needle = " ".join(quote.split()).lower()
        for text, loc in locator_by_text.items():
            if needle in text:
                locator = loc
                break
        findings.append(Finding(
            rule_id=_rule_id("slop", item.get("pattern"), "pattern"),
            category=Category.RESUME_CRAFT,
            gate=Gate.MANAGER,
            severity=Severity.MINOR,
            message=f"{item.get('pattern', 'slop pattern')}: “{quote[:90]}”",
            fix=(item.get("fix") or "Rewrite plainly.")[:160],
            evidence=quote[:200],
            locator=locator,
            provenance=Provenance.HEURISTIC,
            confidence=item.get("confidence", "medium"),
            source="llm:" + "+".join(item.get("providers", [])),
        ))

    return ensemble.PassResult(
        data=findings, providers_used=sorted(per_provider), errors=errors,
        meta={**meta, "samples_per_provider": samples},
    )


def rewrite_pass(
    providers: list[Provider],
    resume: Resume,
    findings: list[Finding],
    objectives: int,
    samples: int,
    use_judge: bool,
    margin: float,
    temperature: float,
    digest: dict | None = None,
) -> ensemble.PassResult:
    """Generate -> fact-check filter -> judge-rank -> polish -> final gate.

    Candidates come from diverse objectives (mechanism/outcome/ownership-led) times
    both providers, not resampling one prompt. Every candidate is fact-checked
    (ensemble.audit_clean) before an LLM forms any opinion of its quality -- the
    quality judge never adjudicates truthfulness, only which fact-checked candidate
    reads best. The judge's #1 pick is lightly polished, and both the polished and
    unpolished forms are handed to the same final gate (ensemble.select_rewrite)
    that plain best-of-N uses, so polishing can only win by actually being better.
    """
    # A finding is rewritable only if its locator names a bullet that actually
    # exists. Resolve that before the top-N cut, not after: a heading locator or an
    # index the model invented would otherwise take a slot and then be dropped,
    # leaving the pass with fewer targets than budgeted -- or none at all.
    bullet_text = {loc: text for loc, text in resume.bullets if text}
    by_locator: dict[str, list[Finding]] = {}
    for finding in findings:
        if finding.locator in bullet_text:
            by_locator.setdefault(finding.locator, []).append(finding)

    ranked = sorted(
        by_locator.items(),
        key=lambda kv: -sum(f.points or 1 for f in kv[1]),
    )[:MAX_REWRITE_TARGETS]

    targets = [
        {
            "locator": locator,
            "bullet": bullet_text[locator],
            "defects": [f"{f.message} -> {f.fix}" for f in items][:5],
        }
        for locator, items in ranked
    ]
    if not targets:
        return ensemble.PassResult(meta={"reason": "no bullets needed rewriting"})

    # -- 3a. Generate: diverse objectives x providers, batched across bullets --
    user = prompts.rewrite_user(targets)
    active_objectives = prompts.OBJECTIVES[: max(1, objectives)]
    jobs = []
    for label, instruction in active_objectives:
        system = prompts.rewrite_system(label, instruction)
        for provider in providers:
            for _ in range(max(1, samples)):
                jobs.append(
                    lambda p=provider, sysprompt=system, obj=label: (
                        p.name, obj, call(p, sysprompt, user, temperature)
                    )
                )

    raw, errors = ensemble.gather(jobs)

    by_target: dict[str, list[tuple[str, str, str, str]]] = {}
    for provider_name, objective, payload in raw:
        for item in payload.get("rewrites") or []:
            locator = (item.get("locator") or "").strip()
            text = (item.get("rewritten") or "").strip()
            if locator and text:
                by_target.setdefault(locator, []).append((
                    text, (item.get("what_changed") or "").strip()[:120],
                    provider_name, objective,
                ))

    # -- 3b. Fact-check every candidate before any quality opinion is formed --
    clean_by_target = {
        target["locator"]: ensemble.audit_clean(
            target["bullet"], by_target.get(target["locator"], [])
        )
        for target in targets
    }
    judged_locators = [loc for loc, clean in clean_by_target.items() if clean]

    judge_errors: list[str] = []
    polish_errors: list[str] = []
    polished: dict[str, str] = {}
    winners: dict[str, dict] = {}

    if use_judge and judged_locators:
        # -- 3c. One batched call ranks every bullet's clean candidates ------
        judge_payload = [
            {
                "locator": loc,
                "original": bullet_text.get(loc, ""),
                "candidates": [
                    {"candidate_id": f"c{i}", "text": c["text"]}
                    for i, c in enumerate(clean_by_target[loc])
                ],
            }
            for loc in judged_locators
        ]
        judge_provider = ensemble.adjudicator_provider(
            providers,
            [c["provider"] for clean in clean_by_target.values() for c in clean],
        )
        judge_raw, judge_errors = ensemble.gather([
            lambda p=judge_provider: call(
                p, prompts.JUDGE_SYSTEM, prompts.judge_user(judge_payload, digest), 0.0
            )
        ])
        rankings: dict[str, list[dict]] = {}
        for payload in judge_raw:
            for entry in payload.get("rankings") or []:
                loc = (entry.get("locator") or "").strip()
                if loc:
                    rankings[loc] = entry.get("order") or []

        # -- 3d. Polish each bullet's #1 (#2 kept only as reference) ---------
        polish_payload = []
        for loc in judged_locators:
            clean = clean_by_target[loc]
            id_to_candidate = {f"c{i}": c for i, c in enumerate(clean)}
            order = rankings.get(loc) or []
            ranked_clean = [
                id_to_candidate[o["candidate_id"]] for o in order
                if o.get("candidate_id") in id_to_candidate
            ]
            if not ranked_clean:
                # Judge failed, skipped this bullet, or hallucinated bad ids --
                # fall back to the deterministic ranking signal.
                ranked_clean = sorted(clean, key=lambda c: -c["rank"])
            winners[loc] = ranked_clean[0]
            entry = {"locator": loc, "original": bullet_text.get(loc, ""),
                      "winner": ranked_clean[0]["text"]}
            if len(ranked_clean) > 1:
                entry["runner_up"] = ranked_clean[1]["text"]
            polish_payload.append(entry)

        if polish_payload:
            polish_provider = ensemble.adjudicator_provider(
                providers, [w["provider"] for w in winners.values()]
            )
            polish_raw, polish_errors = ensemble.gather([
                lambda p=polish_provider: call(
                    p, prompts.POLISH_SYSTEM, prompts.polish_user(polish_payload), 0.0
                )
            ])
            for payload in polish_raw:
                for item in payload.get("polished") or []:
                    loc = (item.get("locator") or "").strip()
                    text = (item.get("rewritten") or "").strip()
                    if loc and text:
                        polished[loc] = text

    # -- 3e. Final gate: the same check for every bullet, judged or not ------
    # A judged bullet offers {polished, unpolished winner} -- both already
    # fact-checked, so this call mainly re-verifies polish didn't regress. An
    # unjudged bullet (Economy mode, or the judge skipped/failed it) offers the
    # full raw candidate pool, so this call does the fact-check itself and
    # behaves as plain best-of-N -- the graceful degradation path.
    rewrites: list[Rewrite] = []
    selection_meta = []
    for target in targets:
        locator = target["locator"]
        winner = winners.get(locator)
        if winner:
            gate_candidates = [(winner["text"], winner["what_changed"], winner["provider"])]
            if locator in polished:
                gate_candidates.insert(
                    0, (polished[locator], "polished", winner["provider"])
                )
        else:
            gate_candidates = [
                (text, what_changed, provider_name)
                for text, what_changed, provider_name, _objective
                in by_target.get(locator, [])
            ]

        chosen, meta = ensemble.select_rewrite(
            target["bullet"], locator, gate_candidates, margin
        )
        selection_meta.append(meta)
        if chosen:
            rewrites.append(chosen)

    hacks = [m for m in selection_meta if m.get("hack_detected")]
    return ensemble.PassResult(
        data=rewrites,
        providers_used=sorted({name for name, _obj, _payload in raw}),
        errors=errors + judge_errors + polish_errors,
        meta={
            "selections": selection_meta,
            "hack_detections": len(hacks),
            "objectives": len(active_objectives),
            "samples_per_objective": max(1, samples),
            "judge_used": use_judge,
            "candidates_generated": sum(len(v) for v in by_target.values()),
            "candidates_audit_clean": sum(len(v) for v in clean_by_target.values()),
            "polished_count": len(polished),
        },
    )
