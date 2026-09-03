"""Derives ats/taxonomy.json from the JD corpus.

Weights come from measured frequency across real postings rather than from an
author's intuition about what matters. That is the point: a weight the corpus does
not support shows up as wrong and can be corrected by adding postings.

Run after changing corpus/jds/:  python scripts/build_taxonomy.py
"""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ats.skill_groups import GROUPS  # noqa: E402

CORPUS = ROOT / "corpus" / "jds"
OUT = ROOT / "ats" / "taxonomy.json"


def _read(path: Path) -> tuple[dict[str, str], str]:
    meta: dict[str, str] = {}
    body: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("#") and ":" in line:
            key, value = line.lstrip("# ").split(":", 1)
            meta[key.strip()] = value.strip()
        else:
            body.append(line)
    return meta, "\n".join(body).lower()


def build() -> dict:
    docs = sorted(CORPUS.glob("*.txt"))
    if not docs:
        sys.exit(f"no corpus documents in {CORPUS}")

    doc_freq: dict[str, int] = defaultdict(int)
    term_freq: dict[str, int] = defaultdict(int)
    sources = []

    for path in docs:
        meta, text = _read(path)
        sources.append({
            "file": path.name,
            "source": meta.get("source", "unknown"),
            "retrieved": meta.get("retrieved", ""),
            "title": meta.get("title", ""),
            "level": meta.get("level", ""),
        })
        for group, terms in GROUPS.items():
            for term, aliases in terms.items():
                count = sum(
                    len(re.findall(rf"(?<!\w){re.escape(a)}(?!\w)", text))
                    for a in aliases
                )
                if count:
                    doc_freq[f"{group}/{term}"] += 1
                    term_freq[f"{group}/{term}"] += count

    total = len(docs)
    entries = {}
    for group, terms in GROUPS.items():
        for term, aliases in terms.items():
            key = f"{group}/{term}"
            df = doc_freq.get(key, 0)
            # Document frequency, not raw count: a term named once in most postings
            # matters more than one named ten times in a single outlier.
            weight = round(df / total, 3)
            entries[key] = {
                "group": group,
                "term": term,
                "aliases": aliases,
                "doc_frequency": df,
                "total_mentions": term_freq.get(key, 0),
                "weight": weight,
                "provenance": "jd-derived" if df else "heuristic",
            }

    return {
        "generated_from": str(CORPUS.relative_to(ROOT)),
        "document_count": total,
        "sources": sources,
        "terms": entries,
    }


if __name__ == "__main__":
    data = build()
    OUT.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    ranked = sorted(data["terms"].values(), key=lambda t: -t["weight"])
    print(f"{data['document_count']} documents -> {OUT.relative_to(ROOT)}")
    print("\ntop terms by document frequency:")
    for entry in ranked[:18]:
        print(f"  {entry['weight']:.2f}  {entry['group']}/{entry['term']}")
    unsupported = [t for t in data["terms"].values() if not t["doc_frequency"]]
    print(f"\n{len(unsupported)} terms unsupported by the corpus (marked heuristic):")
    print("  " + ", ".join(f"{t['group']}/{t['term']}" for t in unsupported) or "  none")
