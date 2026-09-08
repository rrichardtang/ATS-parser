"""Draws the briefs the acceptance set's documents are written from.

08 asked where the test set comes from, and the trap it named is that the cheapest
answer -- a model writing resumes to land on bands a model then scores -- reproduces
exactly the circularity it is meant to remove. What breaks the circle is not who holds
the pen; it is that **nothing the author chooses is aimed at a band**. So the content of
each document is drawn here, from a seeded sampler, before anybody writes a word:

  * **what the candidate has done** is drawn from the job-posting corpus -- the same
    `corpus/jds/` that derives the taxonomy and four of the eight weights. Each work
    item is a requirement line quoted from a posting, with the posting it came from
    recorded beside it. No line in the pool was written for this rubric, and the pool
    is rebuilt from the corpus rather than authored here.
  * **how their resume says it** is drawn per role, on five axes that vary
    independently: whether numbers appear, how specifically things are named, whose
    voice the bullets are in, whether anything after launch is mentioned, and whether
    a setback is admitted. These are properties every resume-writing guide names, and
    they are drawn per role, not per document, so no document's band in any category
    is the outcome of a single choice anybody made.
  * **who the person is** -- track, seniority, employer, domain, register, shape,
    career texture -- is drawn from pools that say nothing about the rubric at all,
    including tracks that are not AI engineering, because a set where every document
    is a strong candidate measures nothing.

The bands the set reaches are therefore **observed afterwards** (`--coverage` on
`scripts/criteria_probe.py`), never targeted. If a band is thin the fix is more seeds,
never an edit to a document that has already been drawn. See
`docs/wayfinder/rubric-migration/acceptance-set.md` for the rule and its limits.

    python scripts/draw_briefs.py                 # rewrite corpus/resumes/briefs.json
    python scripts/draw_briefs.py --show 3        # print briefs, write nothing
    python scripts/draw_briefs.py --count 34      # extend the draw (see the doc first)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

JDS = ROOT / "corpus" / "jds"
OUT = ROOT / "corpus" / "resumes" / "briefs.json"

SEED = 20260908
COUNT = 30

# A pool line is "AI work" if it names the subject matter the four behaviour
# categories are about; everything else is ordinary engineering. The split exists so
# an off-track candidate can be drawn a career that is mostly not this, which is the
# half of the quality spread the fixtures never had.
AI_RE = re.compile(
    r"(?i)\b(ai|ml|llm|llms|model|models|agent|agents|agentic|rag|embedding|"
    r"prompt|prompting|eval|evals|evaluation|inference|fine-tun|transformer|"
    r"nlp|vector|retrieval|machine learning|generative)\b"
)

TRACKS_ON = [
    "LLM platform and serving",
    "RAG systems",
    "Applied ML, models in production",
    "GenAI product engineering",
    "ML infrastructure",
    "NLP",
    "Evaluation and model quality",
    "AI engineering at a startup, no specialism",
    "Forward-deployed / solutions engineering",
    "Agentic AI",
]
TRACKS_OFF = [
    "Data analyst moving toward ML",
    "Backend engineer, no AI work",
    "Full-stack product engineer",
    "Academic researcher leaving the lab",
    "Data engineer / analytics platform",
    "QA and release engineering",
]

SENIORITY = [
    "new graduate", "junior, ~1 year", "junior, ~2 years", "mid, ~4 years",
    "mid, ~5 years", "senior, ~8 years", "senior, ~11 years", "staff, ~14 years",
    "career changer, 2 years in tech after another field",
    "returning after a two-year break",
]

ORG_KINDS = [
    "seed-stage startup (12 people)", "Series B startup (~90 people)",
    "scale-up (~600 people)", "big tech", "an enterprise bank",
    "an insurer", "a national retailer", "a consultancy billing to clients",
    "a government agency", "a university lab", "a non-profit",
    "a contract / freelance stint", "an agency doing client work",
]

DOMAINS = [
    "payments", "fraud and risk", "healthcare notes", "insurance claims",
    "logistics and routing", "e-commerce search", "a two-sided marketplace",
    "adtech", "developer tools", "legal document review", "education",
    "games", "media and publishing", "telecoms", "energy grid data",
    "HR and recruiting", "security operations", "travel booking",
    "agriculture sensing", "local government services",
]

REGISTER = [
    "terse fragments, no articles",
    "full sentences, plain",
    "corporate boilerplate, heavy on nouns",
    "first-person narrative, chatty",
    "dense noun phrases, stack-forward",
    "inconsistent -- some roles edited, some not",
]

BULLET_LENGTH = ["short (under 12 words)", "medium (one line)", "long (runs to two lines)"]

TEXTURE = [
    "nothing unusual", "nothing unusual", "a visible employment gap",
    "two short contract stints", "an internal promotion inside one employer",
    "a role cut short by a layoff", "a career change mid-document",
    "part-time study alongside work", "a parental leave noted in the dates",
]

SUMMARY = ["no summary", "a two-line summary", "an objective statement", "a headline only"]
SKILLS = ["no skills section", "a flat skills list", "skills grouped by kind",
          "a skills table with proficiency levels"]
EXTRAS = ["nothing extra", "a projects section", "publications", "certifications",
          "an interests section", "volunteering"]
EDUCATION = ["education at the top", "education at the bottom", "no education section"]
PAGES = ["one page", "one page, crowded", "two pages", "two pages, second half-empty"]

NUMBERS = ["no numbers anywhere", "a number in about half the bullets",
           "a number in nearly every bullet"]
NAMING = ["names nothing specifically", "names some things, hand-waves others",
          "names the specific systems and tools"]
VOICE = ["first person, singular", "we / the team", "passive, no subject named"]
AFTERMATH = ["stops at the build", "mentions what happened afterwards",
             "describes the afterwards in detail"]
SETBACKS = ["admits nothing that went wrong", "admits something that went wrong"]


DUTY_RE = re.compile(
    r"(?i)^(build|design|own|ship|improve|create|lead|work|analyz|deploy|write|"
    r"develop|contribute|maintain|monitor|take|translate|partner|drive|define|"
    r"implement|iterate|run|support|scale|integrate|instrument|evaluate|debug|"
    r"prototype|collaborate|help|deliver|operate|extend|influence|establish)"
)
JUNK_RE = re.compile(
    r"(?i)(starting point|make space for|equal opportunit|benefits|salary|"
    r"compensation|visa|we offer|about us|mindset|culture|apply |our team is|"
    r"you don't fit|tell us where)"
)


def _bullets(raw: str) -> list[str]:
    """Requirement/responsibility bullets, with wrapped continuation lines rejoined.

    The corpus is hard-wrapped, so reading it line by line yields half-sentences. A
    bullet runs from its marker to the next marker, blank line or heading.
    """
    out: list[str] = []
    current: list[str] = []
    for line in raw.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        marker = bool(re.match(r"^[-*\u2022]\s+", stripped)) or stripped.lower().startswith("nice to have")
        if marker:
            if current:
                out.append(" ".join(current))
            current = [re.sub(r"^[-*\u2022]\s+", "", stripped)]
        elif not stripped:
            if current:
                out.append(" ".join(current))
            current = []
        elif current and line.startswith((" ", "\t")):
            current.append(stripped)
        else:
            if current:
                out.append(" ".join(current))
            current = []
    if current:
        out.append(" ".join(current))
    return [b for b in (b.strip() for b in out) if 40 <= len(b) <= 260 and not JUNK_RE.search(b)]


def _lines_from_txt(path: Path) -> list[str]:
    return _bullets(path.read_text(encoding="utf-8"))


def _lines_from_json(path: Path) -> list[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return _bullets(data.get("raw_text", ""))


def work_pool() -> list[dict]:
    """Every requirement and responsibility bullet in the posting corpus, with where
    it came from.

    Deliberately mechanical: the pool is what the postings say, so nobody can tune it
    toward a criterion without editing a posting, which the taxonomy would notice.
    A bullet is a **duty** if it starts with a verb the postings use for work someone
    does, and a **skill** otherwise -- the qualification lines. A role is written from
    duties, with skills as background.
    """
    pool: list[dict] = []
    seen: set[str] = set()
    for path in sorted(JDS.glob("*.txt")) + sorted((JDS / "user").glob("*.json")):
        lines = _lines_from_txt(path) if path.suffix == ".txt" else _lines_from_json(path)
        for line in lines:
            key = line.lower()
            if key in seen:
                continue
            seen.add(key)
            pool.append({
                "line": line,
                "source": str(path.relative_to(ROOT)),
                "ai": bool(AI_RE.search(line)),
                "kind": "duty" if DUTY_RE.match(line) else "skill",
            })
    return pool


def pool_digest(pool: list[dict]) -> str:
    blob = "\n".join(item["line"] for item in pool)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def draw_role(rng: random.Random, ai: list[dict], ordinary: list[dict],
              duties: list[dict], skills: list[dict], on_track: bool, index: int) -> dict:
    # How much of this role is the subject matter at all is itself a draw. An
    # off-track candidate mostly draws ordinary engineering; an on-track one mostly
    # does not -- but neither is guaranteed, which is the point.
    ai_weight = 0.75 if on_track else 0.2
    # The first item is a responsibility rather than a qualification, so every role
    # has something the person did; the rest is whatever the postings say.
    first = [d for d in duties if d["ai"] == (rng.random() < ai_weight)] or duties
    work: list[dict] = [rng.choice(first)]
    for _ in range(rng.choice([1, 1, 2, 2, 3])):
        source = ai if rng.random() < ai_weight else ordinary
        item = rng.choice(source)
        if item not in work:
            work.append(item)
    background: list[dict] = []
    for _ in range(rng.choice([0, 1, 1, 2])):
        item = rng.choice(skills)
        if item not in background:
            background.append(item)
    return {
        "index": index,
        "org": rng.choice(ORG_KINDS),
        "domain": rng.choice(DOMAINS),
        "months": rng.choice([7, 11, 14, 18, 22, 26, 31, 38, 44, 52]),
        "work": [{"line": w["line"], "source": w["source"]} for w in work],
        "background": [{"line": w["line"], "source": w["source"]} for w in background],
        "detail": {
            "numbers": rng.choice(NUMBERS),
            "naming": rng.choice(NAMING),
            "voice": rng.choice(VOICE),
            "aftermath": rng.choice(AFTERMATH),
            "setbacks": rng.choice(SETBACKS),
        },
    }


def draw(count: int, seed: int) -> dict:
    pool = work_pool()
    duties = [p for p in pool if p["kind"] == "duty"]
    skills = [p for p in pool if p["kind"] == "skill"]
    ai = [p for p in pool if p["ai"]]
    ordinary = [p for p in pool if not p["ai"]]
    briefs = []
    for n in range(1, count + 1):
        # Per-document seed, so extending the draw never moves a brief already written.
        rng = random.Random(f"{seed}:{n}")
        on_track = rng.random() < 0.7
        track = rng.choice(TRACKS_ON if on_track else TRACKS_OFF)
        n_roles = rng.choice([2, 2, 3, 3, 3, 4])
        briefs.append({
            "id": f"{n:02d}",
            "on_track": on_track,
            "track": track,
            "seniority": rng.choice(SENIORITY),
            "register": rng.choice(REGISTER),
            "bullet_length": rng.choice(BULLET_LENGTH),
            "texture": rng.choice(TEXTURE),
            "shape": {
                "summary": rng.choice(SUMMARY),
                "skills": rng.choice(SKILLS),
                "education": rng.choice(EDUCATION),
                "extras": rng.choice(EXTRAS),
                "pages": rng.choice(PAGES),
            },
            "roles": [draw_role(rng, ai, ordinary, duties, skills, on_track, i)
                      for i in range(n_roles)],
        })
    return {
        "seed": seed,
        "count": count,
        "work_pool": {
            "lines": len(pool),
            "duties": len(duties),
            "subject_matter": len(ai),
            "ordinary": len(ordinary),
            "skills": len(skills),
            "sources": sorted({p["source"] for p in pool}),
            "digest": pool_digest(pool),
        },
        "note": (
            "Drawn by scripts/draw_briefs.py before any document was written. Nothing "
            "here names a category, a criterion or a band. Bands are observed after "
            "the fact and never targeted; see docs/wayfinder/rubric-migration/"
            "acceptance-set.md."
        ),
        "briefs": briefs,
    }


def render(brief: dict) -> str:
    lines = [f"--- brief {brief['id']} " + ("(on track)" if brief["on_track"] else "(off track)")]
    lines.append(f"  track      {brief['track']}")
    lines.append(f"  seniority  {brief['seniority']}")
    lines.append(f"  register   {brief['register']}; bullets {brief['bullet_length']}")
    lines.append(f"  texture    {brief['texture']}")
    shape = brief["shape"]
    lines.append("  shape      " + "; ".join(shape[k] for k in
                 ("summary", "skills", "education", "extras", "pages")))
    for role in brief["roles"]:
        d = role["detail"]
        lines.append(f"  role {role['index']}: {role['org']}, {role['domain']}, "
                     f"{role['months']} months")
        lines.append(f"     writes: {d['numbers']}; {d['naming']}; {d['voice']}; "
                     f"{d['aftermath']}; {d['setbacks']}")
        for w in role["work"]:
            lines.append(f"     - {w['line']}")
        for w in role["background"]:
            lines.append(f"     . {w['line']}")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--count", type=int, default=COUNT)
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--show", type=int, default=0,
                    help="print this many briefs and write nothing")
    args = ap.parse_args()

    drawn = draw(args.count, args.seed)
    if args.show:
        for brief in drawn["briefs"][:args.show]:
            print(render(brief))
        return
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(drawn, indent=2) + "\n", encoding="utf-8")
    pool = drawn["work_pool"]
    print(f"{drawn['count']} briefs from {pool['lines']} posting bullets "
          f"({pool['duties']} responsibilities, {pool['skills']} qualifications; "
          f"{pool['subject_matter']} subject-matter, {pool['ordinary']} ordinary) -> "
          f"{OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
