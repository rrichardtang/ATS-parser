"""Build prototype/06-criterion-scoring.html -- THROWAWAY, ticket 06's prototype.

The five specs and the weights are inlined into the page so it opens by double-click
with nothing installed. Regenerate with:

    python prototype/build_06_prototype.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ats import config, rubric, score  # noqa: E402

OUT = Path(__file__).with_name("06-criterion-scoring.html")

SPECS = rubric.load_specs()
WEIGHTS = {c.value: w for c, w in config.category_weights().items()}
SHARES = {c.value: s for c, s in score.rule_shares().items()}
RULE_ONLY = [c for c in WEIGHTS if c not in SHARES]

DATA = json.dumps(
    {"specs": SPECS, "weights": WEIGHTS, "shares": SHARES, "ruleOnly": RULE_ONLY},
    indent=1,
)

PAGE = Path(__file__).with_name("06-criterion-scoring.template.html").read_text(encoding="utf-8")
OUT.write_text(PAGE.replace("/*__DATA__*/null", DATA), encoding="utf-8")
print(f"wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size // 1024} KB)")
