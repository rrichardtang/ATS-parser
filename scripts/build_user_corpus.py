"""Derives ats/taxonomy.json and ats/jd_digest.json from your personal JD corpus
(corpus/jds/user/*.json) -- real postings you're targeting, not the generic
synthesized composite corpus.

Free, deterministic, no API key: section classification and dimension detection
are both regex over text you already pasted (see ats/jd_sections.py,
ats/jd_dimensions.py). Run this after every posting you add with
scripts/add_jd.py; it fully regenerates both output files from the current
contents of corpus/jds/user/, so nothing here is ever hand-edited.

With zero files in corpus/jds/user/, this is a no-op: it leaves whatever
ats/taxonomy.json the generic corpus produced alone, and does not write
ats/jd_digest.json at all -- so nothing downstream behaves differently until you
add a posting.
"""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ats import jd_dimensions, jd_sections  # noqa: E402
from ats.skill_groups import GROUPS  # noqa: E402

CORPUS = ROOT / "corpus" / "jds" / "user"
TAXONOMY_OUT = ROOT / "ats" / "taxonomy.json"
DIGEST_OUT = ROOT / "ats" / "jd_digest.json"

# Nice-to-have mentions still count toward keyword coverage, just at reduced
# weight relative to a requirements-section mention.
NICE_WEIGHT_FACTOR = 0.4
TOP_N_IN_DIGEST = 20


def _count(text: str, aliases: list[str]) -> int:
    return sum(len(re.findall(rf"(?<!\w){re.escape(a)}(?!\w)", text)) for a in aliases)


def build(corpus_dir: Path = CORPUS) -> dict | None:
    docs = sorted(corpus_dir.glob("*.json"))
    if not docs:
        return None

    postings = [json.loads(p.read_text(encoding="utf-8")) for p in docs]
    total = len(postings)

    required_df: dict[str, int] = defaultdict(int)
    nice_df: dict[str, int] = defaultdict(int)
    mentions: dict[str, int] = defaultdict(int)
    dimension_df: dict[str, int] = defaultdict(int)
    per_posting_dimensions: list[set[str]] = []
    target_titles: list[str] = []
    sources = []

    for posting in postings:
        raw_text = posting.get("raw_text", "")
        title = posting.get("title", "").strip()
        if title and title not in target_titles:
            target_titles.append(title)
        sources.append({
            "title": title,
            "company": posting.get("company", ""),
            "date_added": posting.get("date_added", ""),
        })

        spans = jd_sections.classify(raw_text)
        required_text = spans[jd_sections.REQUIRED].lower()
        nice_text = spans[jd_sections.NICE].lower()
        responsibilities_text = spans[jd_sections.RESPONSIBILITIES].lower()

        # Dimension phrases ("own production systems end-to-end") describe scope,
        # so they live as naturally in "About the Role" as in "Requirements" --
        # unlike skill terms below, responsibilities text is included here, not
        # excluded. Only the noise/benefits bucket is left out.
        hits = jd_dimensions.scan(f"{required_text}\n{nice_text}\n{responsibilities_text}")
        per_posting_dimensions.append(hits)
        for dim in hits:
            dimension_df[dim] += 1

        for group, terms in GROUPS.items():
            for term, aliases in terms.items():
                key = f"{group}/{term}"
                r = _count(required_text, aliases)
                n = _count(nice_text, aliases)
                if r:
                    required_df[key] += 1
                    mentions[key] += r
                if n:
                    nice_df[key] += 1
                    mentions[key] += n

    entries = {}
    for group, terms in GROUPS.items():
        for term, aliases in terms.items():
            key = f"{group}/{term}"
            rdf, ndf = required_df.get(key, 0), nice_df.get(key, 0)
            weight = round((rdf + NICE_WEIGHT_FACTOR * ndf) / total, 3)
            entries[key] = {
                "group": group,
                "term": term,
                "aliases": aliases,
                "doc_frequency": rdf + ndf,
                "required_doc_frequency": rdf,
                "nice_doc_frequency": ndf,
                "total_mentions": mentions.get(key, 0),
                "weight": weight,
                "provenance": "jd-derived" if (rdf or ndf) else "heuristic",
            }

    taxonomy = {
        "generated_from": str(corpus_dir),
        "document_count": total,
        "sources": sources,
        "terms": entries,
    }

    def _ranked(df_map: dict[str, int]) -> list[dict]:
        ranked = sorted(
            ({"term": k, "doc_frequency": v} for k, v in df_map.items() if v),
            key=lambda e: -e["doc_frequency"],
        )
        return ranked[:TOP_N_IN_DIGEST]

    digest = {
        "document_count": total,
        "target_titles": target_titles,
        "required": _ranked(required_df),
        "nice_to_have": _ranked(nice_df),
        "dimensions": {
            name: {"count": dimension_df.get(name, 0), "total": total}
            for name in jd_dimensions.DIMENSIONS
        },
        # What ticket 04 derives category weight from: how many postings state the
        # behaviour a category measures. A category is a union of dimensions, so this
        # cannot be summed from the per-dimension counts above -- one posting stating
        # two of a category's behaviours still counts once.
        "category_document_frequency": {
            category: {"count": count, "total": total}
            for category, count in jd_dimensions.category_document_frequency(
                per_posting_dimensions
            ).items()
        },
        "sources": sources,
    }

    return {"taxonomy": taxonomy, "digest": digest}


if __name__ == "__main__":
    result = build()
    if result is None:
        print(f"No postings in {CORPUS.relative_to(ROOT)} -- nothing to do.")
        print("Add one with `python scripts/add_jd.py`, then run this again.")
        sys.exit(0)

    TAXONOMY_OUT.write_text(json.dumps(result["taxonomy"], indent=2) + "\n", encoding="utf-8")
    DIGEST_OUT.write_text(json.dumps(result["digest"], indent=2) + "\n", encoding="utf-8")

    n = result["taxonomy"]["document_count"]
    print(f"{n} posting(s) -> {TAXONOMY_OUT.relative_to(ROOT)}, {DIGEST_OUT.relative_to(ROOT)}")

    print("\ntarget titles:", ", ".join(result["digest"]["target_titles"]) or "(none)")

    print("\nrequired, by document frequency:")
    for e in result["digest"]["required"][:12]:
        print(f"  {e['doc_frequency']}/{n}  {e['term']}")

    print("\nnice-to-have:")
    for e in result["digest"]["nice_to_have"][:8]:
        print(f"  {e['doc_frequency']}/{n}  {e['term']}")

    print("\ndimensions:")
    for name, d in result["digest"]["dimensions"].items():
        print(f"  {d['count']}/{d['total']}  {name}")

    print("\nbehaviour document frequency (what category weight derives from):")
    for name, d in result["digest"]["category_document_frequency"].items():
        print(f"  {d['count']}/{d['total']}  {name}")
