"""Measures how often a shipped rewrite makes the problem it was asked to fix go away.

For one document: score it and run pass 3 as the app does, run the content judge a
second time on the unchanged resume (the control), then swap every shipped rewrite in
and run the deterministic rules and the content judge again. Each finding pass 3 handed
a writer is then one of
fixed / not_fixed / not_shipped (and why) / not_swapped / unmeasured.

The control is the noise floor. The judges change their own answer about 12% of the
time between samples, so some content findings vanish with no edit at all; the fix rate
of a content-judge finding means little until it is set beside that. Deterministic
findings have no such noise. Slop-pass findings are not re-run after the swap, so a
shipped rewrite against one is `unmeasured`, as is a content finding when the content
judge failed after the swap.

The pure half lives here so it tests without a network; scripts/rewrite_harness.py
drives it.
"""
from __future__ import annotations

import copy
import re
from collections import Counter
from dataclasses import replace

from . import budget, config, passes, pipeline, prompts
from .extract import extract
from .models import Finding, Rewrite
from .sections import Resume, parse

KINDS = ("deterministic", "content", "slop")
OUTCOMES = ("fixed", "not_fixed", "not_shipped", "not_swapped", "unmeasured")


def swap_text(text: str, original: str, rewritten: str) -> str | None:
    """`text` with the first run of `original` replaced, matching across any
    whitespace (a wrapped bullet is one line in the parse and several in the text)."""
    pattern = r"\s+".join(map(re.escape, original.split()))
    swapped, count = re.subn(pattern, lambda _: rewritten, text, count=1)
    return swapped if count else None


def swap(text: str, resume: Resume, rewrites: list[Rewrite]) -> tuple[str, Resume, set[str]]:
    """The text and a copy of the resume with each rewrite in place of its bullet, and
    the locators whose original could not be found in the text (left unswapped)."""
    resume = copy.deepcopy(resume)
    missed: set[str] = set()
    for rewrite in rewrites:
        swapped = swap_text(text, rewrite.original, rewrite.rewritten)
        if swapped is None:
            missed.add(rewrite.locator)
            continue
        text = swapped
        role, bullet = map(int, re.findall(r"\d+", rewrite.locator))
        resume.roles[role].bullets[bullet] = rewrite.rewritten
    return text, resume, missed


def not_shipped_reason(selection: dict | None) -> str:
    """Why `select_rewrite` kept the original, as a bucket that quotes nothing."""
    if selection is None:
        return "no selection"
    if selection.get("reason") == "no candidates":
        return "no candidates"
    return "audit rejected" if selection.get("rejected_for_audit") else "no margin"


def classify(
    handed: list[tuple[str, list[Finding]]], kinds: dict[tuple[str, str], str],
    rewrites: list[Rewrite], selections: list[dict], missed: set[str],
    after: set[tuple[str, str]], content_measured: bool,
) -> list[dict]:
    """One entry per (locator, rule_id) that pass 3 handed a writer. `after` is every
    (locator, rule_id) the deterministic rules and the content judge report on the
    swapped document."""
    shipped = {r.locator for r in rewrites}
    selection_of = {s["locator"]: s for s in selections}
    entries = []
    for locator, items in handed:
        for rule_id in dict.fromkeys(f.rule_id for f in items):
            kind = kinds.get((locator, rule_id), "slop")
            entry = {"locator": locator, "rule_id": rule_id, "kind": kind, "reason": "",
                     "evidence": next(f.evidence for f in items if f.rule_id == rule_id)}
            if locator not in shipped:
                entry["outcome"] = "not_shipped"
                entry["reason"] = not_shipped_reason(selection_of.get(locator))
            elif locator in missed:
                entry["outcome"] = "not_swapped"
            elif kind == "slop" or (kind == "content" and not content_measured):
                entry["outcome"] = "unmeasured"
            else:
                entry["outcome"] = "not_fixed" if (locator, rule_id) in after else "fixed"
            entries.append(entry)
    return entries


def control_counts(before: list[Finding], control: list[Finding]) -> dict[str, int]:
    """How many placed content findings the unchanged resume lost on a second asking."""
    kept = {(f.locator, f.rule_id) for f in control}
    keys = {(f.locator, f.rule_id) for f in before}
    return {"findings": len(keys), "vanished": len(keys - kept)}


def evaluate(name: str, path: str, providers, others, settings: dict) -> dict:
    """Before, control and after for one document; the raw record `tally` reads."""
    doc = extract(path)
    resume = parse(doc.text)
    skipped = "no text layer" if not doc.has_text_layer else passes.withholding_reason(resume)
    if skipped:
        return {"name": name, "skipped": skipped}
    title = pipeline.resolve_target_title("")
    digest = config.jd_digest()

    def content(res: Resume, text: str, deterministic: list[Finding]):
        return passes.content_pass(
            providers, res, text, "", deterministic, int(settings["content_votes"]),
            float(settings["temperature"]), digest)

    deterministic = pipeline.deterministic(doc, resume, "", title)
    before = content(resume, doc.text, deterministic)
    slop = passes.slop_pass(
        others, resume, [f.evidence for f in deterministic if f.rule_id.startswith("slop/")],
        int(settings["slop_samples"]), int(settings["slop_vote_k"]),
        float(settings["temperature"]))
    findings = deterministic + before.data + slop.data
    rewrite = passes.rewrite_pass(
        others, resume, findings, int(settings["rewrite_objectives"]),
        int(settings["rewrite_samples"]), bool(settings["rewrite_judge"]),
        float(settings["rewrite_margin"]), float(settings["temperature"]), digest)

    control = content(resume, doc.text, deterministic)
    text, swapped, missed = swap(doc.text, resume, rewrite.data)
    deterministic_after = pipeline.deterministic(replace(doc, text=text), swapped, "", title)
    after = content(swapped, text, deterministic_after)

    kinds = {(f.locator, f.rule_id): "content" for f in before.data}
    kinds |= {(f.locator, f.rule_id): "deterministic" for f in deterministic}
    after_keys = {(f.locator, f.rule_id) for f in deterministic_after + after.data}
    return {
        "name": name,
        "targets": classify(passes.rewrite_targets(resume, findings), kinds, rewrite.data,
                            rewrite.meta.get("selections", []), missed, after_keys,
                            not after.errors),
        "control": None if control.errors else control_counts(before.data, control.data),
        "rewrites": [r.model_dump() for r in rewrite.data],
        "selections": rewrite.meta.get("selections", []),
        "errors": {label: result.errors for label, result in
                   [("before", before), ("slop", slop), ("rewrite", rewrite),
                    ("control", control), ("after", after)] if result.errors},
    }


def tally(documents: list[dict]) -> dict:
    """Counts only: outcomes by kind, not-shipped reasons, and the control."""
    outcomes = {kind: Counter() for kind in KINDS}
    reasons: Counter = Counter()
    control = Counter()
    for document in documents:
        for target in document.get("targets", []):
            outcomes[target["kind"]][target["outcome"]] += 1
            reasons[target["reason"]] += bool(target["reason"])
        control.update(document.get("control") or {})
    return {"outcomes": {k: dict(v) for k, v in outcomes.items()},
            "not_shipped_reasons": dict(+reasons),
            "control": {"findings": control["findings"], "vanished": control["vanished"]}}


def summary(run: dict) -> dict:
    """The counts-only record that is safe to commit: rule ids and locators, no text."""
    documents = run["documents"]
    return {
        "total": tally(documents),
        "documents": {
            d["name"]: {"skipped": d["skipped"]} if "skipped" in d else {
                **tally([d]),
                "targets": [{k: t[k] for k in ("locator", "rule_id", "kind", "outcome", "reason")}
                            for t in d["targets"]],
            } for d in documents},
    }


def _rate(part: int, whole: int) -> str:
    return f"{part / whole:.0%}" if whole else "n/a"


def fix_rate(counts: dict[str, int]) -> str:
    return _rate(counts.get("fixed", 0), counts.get("fixed", 0) + counts.get("not_fixed", 0))


def render(run: dict) -> str:
    """The table: counts per document and in total. Quotes no resume text."""
    documents = run["documents"]
    head = f"{'document':<22}{'kind':<14}" + "".join(f"{o:>13}" for o in OUTCOMES) + f"{'fix rate':>10}"
    rows = [head]
    for label, group in [*((d["name"], [d]) for d in documents if "skipped" not in d),
                         ("TOTAL", documents)]:
        counts = tally(group)["outcomes"]
        for kind in KINDS:
            rows.append(f"{label:<22}{kind:<14}"
                        + "".join(f"{counts[kind].get(o, 0):>13}" for o in OUTCOMES)
                        + f"{fix_rate(counts[kind]):>10}")
    skipped = [f"{d['name']}: {d['skipped']}" for d in documents if "skipped" in d]
    total = tally(documents)
    control = total["control"]
    rows += ["", f"Control (no edit): {control['vanished']} of {control['findings']} "
                 f"content findings vanished ({_rate(control['vanished'], control['findings'])}) "
                 f"-- the noise floor for the content fix rate "
                 f"({fix_rate(total['outcomes']['content'])}).",
             "Not shipped, by reason: " + (", ".join(
                 f"{r} {n}" for r, n in total["not_shipped_reasons"].items()) or "none")]
    return "\n".join(rows + [f"Skipped: {s}" for s in skipped])


def call_counts(settings: dict) -> dict[str, int]:
    """Calls per provider per document: three content runs, slop, and pass 3."""
    generate = int(settings["rewrite_objectives"]) * int(settings["rewrite_samples"])
    return {"content": 3 * int(settings["content_votes"]),
            "slop": int(settings["slop_samples"]),
            "rewrite": generate, "judge and polish": 2 * bool(settings["rewrite_judge"])}


def worst_case(providers, others, settings: dict, documents: list[tuple[Resume, str, list[Finding]]],
               price) -> float:
    """Dollars, every reply at its cap and every call repaired (ats/budget.py).

    Pass 3's prompts are estimated from the longest the writer is sent: six bullets with
    a 260-character defect each; the judge and polish calls also carry every candidate.
    """
    counts = call_counts(settings)
    digest = config.jd_digest()
    content = [budget.input_tokens(*passes.content_prompt(r, text, "", dets, digest))
               for r, text, dets in documents]
    slop = [budget.input_tokens(prompts.SLOP_SYSTEM, prompts.slop_user(r, []))
            for r, _, _ in documents]
    label, instruction = prompts.OBJECTIVES[0]
    writer = [budget.input_tokens(
        prompts.rewrite_system(label, instruction),
        prompts.rewrite_user([{"locator": loc, "bullet": text, "defects": ["x" * 260]}
                              for loc, text in r.bullets[:passes.MAX_REWRITE_TARGETS]]))
        for r, _, _ in documents]
    candidates = 1 + int(settings["rewrite_objectives"]) * int(settings["rewrite_samples"])
    phases = [(providers, content, counts["content"]), (others, slop, counts["slop"]),
              (others, writer, counts["rewrite"]),
              (others, [t * candidates for t in writer], counts["judge and polish"])]
    return sum(sum(budget.worst_case(group, tokens, {p.name: calls for p in group},
                                     False, price).values())
               for group, tokens, calls in phases)
