"""Prompts for the three passes. Terseness is enforced here and again in code.

Pass 1 judges substance. Pass 2 judges slop, in its own call so it gets undivided
attention. Pass 3 rewrites, after both, so a rewrite fixes content and slop in one
edit rather than trading one for the other.
"""
from __future__ import annotations

import functools
import json

from . import rubric
from .models import JUDGED_CATEGORIES
from .sections import Resume

TERSE = """
Write like a code reviewer, not a coach. Every item is a specific defect, where it
is, and the fix. No preamble, no encouragement, no restating the resume back, no
summary at the end. Never praise. If something is fine, say nothing about it.
""".strip()

NO_INVENTION = """
Never invent a fact. You may only use information present in the resume. If a
claim would need a number, a scale, or a tool the resume does not contain, say so
rather than supplying a plausible one. A fabricated figure is not a style problem;
it is something the candidate has to defend in an interview.
""".strip()

# Ticket 05: the content pass asks the **criteria**. The model answers, per category,
# the five binary evidence questions in that category's spec, each with the quote that
# settles it. It names no band and authors no number -- the band is a lookup from the
# answers (`ats.rubric.band_of`) and the value is a lookup from the band.
#
# The criteria are read from the specs rather than restated here, so the questions the
# model answers and the questions the band lookup reads can never drift apart.


def criteria_block() -> str:
    """The five specs, rendered as the questions a judge answers.

    `yes_requires` and `no_looks_like` travel with each question on purpose: they are
    what makes two judges answer the same way, and they are the whole of the anchoring
    the old "score each category 0-100" prompt never had.
    """
    lines: list[str] = []
    for spec in rubric.load_specs():
        lines.append(f"## {spec['category']}")
        lines.append(spec["measures"])
        for criterion in spec["criteria"]:
            lines.append(f"{criterion['id']} ({criterion['name']}): {criterion['question']}")
            lines.append(f"    yes requires: {criterion['yes_requires']}")
            lines.append(f"    no looks like: {criterion['no_looks_like']}")
        lines.append("")
    return "\n".join(lines).strip()


@functools.lru_cache(maxsize=1)
def content_system() -> str:
    """Built once from the specs. A function rather than a constant so importing the
    package does not read five JSON files before anything asks for a prompt."""
    return f"""
You review resumes for mid-level AI Engineer roles (about 3 years of experience).

{TERSE}

{NO_INVENTION}

Judge only what static analysis cannot. Deterministic rules have already checked
formatting, section structure, quantification rate, keyword coverage and writing
patterns; their findings are given to you. Do not repeat them.

Your job is to ANSWER THE CRITERIA below -- every one of them, for every category.
Each is a yes/no question about evidence that is either in the resume or is not.

{criteria_block()}

Rules for answering, none of them optional:
- Answer every criterion in every category. Do not skip one, and do not invent one.
- Do not name a band. Do not give a category a score. Neither is yours to choose:
  both are computed from these answers.
- "yes" requires an EXACT QUOTE from the resume in "evidence", and the "locator" of
  the place it came from, copied verbatim from the PLACES list you are given.
- "no" comes in two shapes, and the difference matters:
  * nothing in the resume speaks to the question at all -- leave "evidence" and
    "locator" empty and say in "why" what is absent. There is nothing to quote.
  * the resume does speak to it and what it says is the problem -- quote it and
    locate it, exactly as a "yes" would, and give the fix.
- NEVER write a locator that is not in the PLACES list. A quote you cannot place is
  worth less than no quote: say what is absent instead.

Return JSON only:
{{
  "categories": {{
    "<category name>": {{
      "criteria": [
        {{"id": "<C1..C5>",
          "answer": "yes" | "no",
          "evidence": "<exact quote from the resume, or empty>",
          "locator": "<a locator from PLACES, or empty>",
          "why": "<one line: what the quote settles, or what is absent>",
          "fix": "<what to do about it -- only when the answer is no>"}}
      ]
    }}
  }}
}}
""".strip()


SLOP_SYSTEM = f"""
You detect AI-generated writing patterns in resumes.

{TERSE}

Rules, in order of importance:
1. Do NOT guess whether AI wrote this, and do NOT score how AI-like it is.
   Detectors guess; named patterns are evidence the reader can check.
2. Name the pattern, quote the exact line, give the fix in a few words.
3. Do NOT rewrite anything. That is a separate pass.
4. A resume is terse and somewhat uniform by design. Do not flag it for lacking
   conversational cadence, digressions, or personality. Formal is not slop.
5. Do not flag a term that is the ordinary technical name for the thing --
   "eval harness" and "robustness to noise" are standard vocabulary.

Patterns to look for, beyond what regex already caught:
- Synonym cycling: rotating built/created/developed/engineered for one idea.
- Robotic rhythm: every bullet the same shape and length.
- Hollow specificity: technical words arranged to sound precise while saying
  nothing checkable ("leveraged advanced architectures to optimize performance").
- Portability: a line that could move unchanged to another candidate, company, or
  product. This is the strongest signal for resume bullets.
- Importance puffery and significance claims that state no fact.

Return JSON only:
{{"findings": [{{"pattern": "<short name>", "quoted_line": "<exact text>",
                "fix": "<a few words>"}}]}}
Findings without an exact quote are discarded.
""".strip()

# Pass 3 generates from three lenses instead of resampling the same prompt for
# variety. Each lens leads with a different bullet invariant (see ats/invariants.py)
# rather than an unrelated new taxonomy, so generation stays aligned with what
# scoring already checks for.
OBJECTIVES = [
    ("mechanism", "Foreground the technical HOW -- the specific method, tool, or "
                  "design choice that made this possible. Do not bury it behind "
                  "generic phrasing."),
    ("outcome", "Foreground the RESULT -- what changed because of this work, "
                "stated as plainly as the original bullet supports."),
    ("ownership", "Foreground OWNERSHIP AND SCOPE -- what this person specifically "
                  "did and owned, versus the team, without inflating scope beyond "
                  "what the original states."),
]


def rewrite_system(objective_label: str, objective_instruction: str) -> str:
    return f"""
You rewrite weak resume bullets for a mid-level AI Engineer.

{NO_INVENTION}

This pass's lens -- {objective_label}: {objective_instruction}
Still fix every named defect; the lens changes emphasis, not which defects get fixed.

Method:
- Make the MINIMUM effective edit. Fix the named defects; leave the rest alone.
- Preserve the candidate's meaning and voice. Do not smooth everything into the
  same polished register.
- Keep every claim the original made. Do not drop content to make it shorter.
- Where the bullet needs a number the candidate never gave, insert a typed
  placeholder in square brackets -- [add: eval metric], [add: scale],
  [add: latency] -- so they supply the real figure. NEVER invent one.
- Do not add numbers that merely count people, tools or meetings. "Collaborated
  with 3 engineers" measures nothing.

Return JSON only:
{{"rewrites": [{{"locator": "<locator>", "rewritten": "<the bullet>",
                "what_changed": "<one clause>"}}]}}
""".strip()


JUDGE_SYSTEM = """
You rank candidate rewrites of resume bullets by writing quality.

Every candidate you see has already passed a fact-check against its original
bullet -- your job is judging quality, not truthfulness. Do not second-guess
whether a claim is true; assume it is and judge only how well it's written.

Rank on: impact (does it state why the work mattered), specificity (concrete
technical detail), technical depth (real engineering complexity, not jargon),
clarity (a recruiter understands it in one read), credibility (sounds believable,
not inflated), ATS relevance (natural technical terminology, not stuffed).

Do NOT reward: buzzwords, adjectives like "cutting-edge" or "robust", vague
statements, or inflated impact. A shorter, plainer bullet beats a longer,
decorated one if it says more with less.

For each bullet, return its candidates in rank order (best first), each with one
clause of rationale. Do not assign numeric scores -- rank order only.

Return JSON only:
{"rankings": [{"locator": "<locator>",
               "order": [{"candidate_id": "<id>", "why": "<one clause>"}]}]}
""".strip()

POLISH_SYSTEM = f"""
You lightly polish the single best-ranked rewrite of a resume bullet.

{NO_INVENTION}

You are given the WINNER (already fact-checked and ranked #1 on quality) and, for
reference only, the RUNNER-UP. Tighten the winner's wording: cut filler, sharpen a
verb, fix an awkward clause. You may borrow a specific phrase from the runner-up
ONLY if every fact in that phrase already appears in the winner or the original
bullet. Never introduce an adjective, claim, or emphasis absent from the winner.
Do not blend the two into something neither one said. If the winner is already
tight, return it unchanged.

Return JSON only:
{{"polished": [{{"locator": "<locator>", "rewritten": "<the polished bullet>",
                "what_changed": "<one clause, or 'none' if unchanged>"}}]}}
""".strip()

# The five categories a judge is asked about, named from the enum so the prompt and
# `passes.CATEGORY_BY_NAME` can never drift apart. The three rule-only categories --
# `Parseability`, `Structure & formatting`, `Title & seniority alignment` -- are
# deliberately absent: nothing a model says about them is used.
#
# Ticket 05 changed what is asked *of* these five: the prompt no longer requests a score
# per category, it requests an answer per criterion with the quote behind it. The names
# stay, and they are still what a reply is keyed on.
CATEGORY_NAMES = [c.value for c in JUDGED_CATEGORIES]


def digest_text(digest: dict) -> str:
    """A compact summary of the user's curated JD corpus (scripts/build_user_corpus.py),
    for LLM prompts -- always fits, unlike a truncated raw posting, and reflects every
    postings the user has added, not just whichever one fit first.
    """
    if not digest:
        return ""
    n = digest.get("document_count", 0)
    lines = [f"Grounded in {n} posting(s) you're targeting:"]
    required = digest.get("required") or []
    if required:
        lines.append("Required in most: " + ", ".join(
            f"{e['term'].split('/', 1)[-1]} ({e['doc_frequency']}/{n})" for e in required[:10]
        ))
    nice = digest.get("nice_to_have") or []
    if nice:
        lines.append("Nice-to-have: " + ", ".join(
            e["term"].split("/", 1)[-1] for e in nice[:6]
        ))
    dims = {k: v for k, v in (digest.get("dimensions") or {}).items() if v.get("count")}
    if dims:
        lines.append("Emphasized qualities: " + ", ".join(
            f"{name} ({d['count']}/{d['total']})" for name, d in dims.items()
        ))
    return "\n".join(lines)


def places(resume: Resume) -> list[str]:
    """Every locator a criterion answer is allowed to name, with the text at it.

    The baseline run had 10% of locators naming nothing in the parsed resume --
    `exp[0]`, `skills`, and one compound locator addressing two bullets at once. A
    model that is shown the addresses it may use has no reason to invent one, and
    `passes` drops the ones it invents anyway.
    """
    out = []
    if resume.summary:
        out.append(f"summary: {resume.summary}")
    out += [f"{locator}: {text}" for locator, text in resume.bullets]
    return out


def content_user(
    resume: Resume, full_text: str, jd_text: str, findings_summary: list[str],
    digest: dict | None = None,
) -> str:
    parts = [
        "RESUME:",
        full_text[:12000],
        "",
        f"PARSED: {resume.years_experience} years across {len(resume.roles)} roles; "
        f"sections: {', '.join(resume.section_order) or 'none detected'}.",
        "",
        "PLACES (the only locators you may use):",
        "\n".join(places(resume)) or "(none)",
        "",
        "ALREADY FOUND BY STATIC RULES (do not repeat these):",
        "\n".join(f"- {f}" for f in findings_summary[:40]) or "- none",
        "",
        f"ANSWER EVERY CRITERION IN EACH CATEGORY: {', '.join(CATEGORY_NAMES)}",
    ]
    digest_summary = digest_text(digest or {})
    if digest_summary:
        parts += ["", "TARGET ROLE SIGNAL:", digest_summary]
    if jd_text.strip():
        parts += ["", "ALSO CONSIDER THIS SPECIFIC POSTING:", jd_text[:6000]]
    return "\n".join(parts)


def slop_user(resume: Resume, caught: list[str]) -> str:
    bullets = [f"{loc}: {text}" for loc, text in resume.bullets]
    return "\n".join([
        "SUMMARY SECTION:",
        resume.summary or "(none)",
        "",
        "BULLETS:",
        "\n".join(bullets) or "(none)",
        "",
        "ALREADY CAUGHT BY REGEX (do not repeat):",
        "\n".join(f"- {c}" for c in caught[:30]) or "- none",
    ])


def rewrite_user(targets: list[dict]) -> str:
    return (
        "Rewrite each bullet below. Fix every defect listed with it.\n\n"
        + json.dumps(targets, indent=2)
    )


def judge_user(targets: list[dict], digest: dict | None = None) -> str:
    """targets: [{"locator", "original", "candidates": [{"candidate_id", "text"}]}].

    Provider and objective are deliberately withheld -- a judge that knew which
    model or lens produced a candidate could favor it on that basis rather than
    the writing itself.
    """
    parts = ["Rank each bullet's candidates.\n"]
    digest_summary = digest_text(digest or {})
    if digest_summary:
        parts += ["Grade ATS relevance against this, not generic terminology:", digest_summary, ""]
    parts.append(json.dumps(targets, indent=2))
    return "\n".join(parts)


def polish_user(targets: list[dict]) -> str:
    """targets: [{"locator", "original", "winner", "runner_up"}]. runner_up may be
    absent when a bullet had only one audit-clean candidate."""
    return "Polish each bullet's winner.\n\n" + json.dumps(targets, indent=2)
