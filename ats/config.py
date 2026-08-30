"""Loads weights.toml. Every tunable number lives there, not scattered in code."""
from __future__ import annotations

import functools
import json
import tomllib
from pathlib import Path
from typing import Any

from .models import Category, Provenance, Severity

CONFIG_PATH = Path(__file__).with_name("weights.toml")
JD_DIGEST_PATH = Path(__file__).with_name("jd_digest.json")

SEVERITY_ORDER = {Severity.MINOR: 0, Severity.MAJOR: 1, Severity.CRITICAL: 2}

# Which existing rule a JD-derived dimension amplifies. Never a new rubric axis --
# only ever scales how much an already-judged rule costs, for this user's runs.
# See ats/jd_dimensions.py for what each dimension detects and why "leadership"
# and cross-functional collaboration aren't wired in here yet.
RULE_DIMENSION = {
    "content/ownership": "ownership",
    "cred/no-production": "production",
    "cred/notebook-only": "production",
    "cred/no-evaluation": "evaluation",
    "title/seniority-mismatch": "seniority",
}
# A dimension mentioned in every posting scales its rule's cost up to 1.5x; one
# your postings never mention leaves it at the default 1.0x. Only ever amplifies
# -- a dimension your target roles don't care about doesn't make the underlying
# rule less true in general, so it never scales below baseline.
DIMENSION_MAX_MULTIPLIER = 1.5


@functools.lru_cache(maxsize=1)
def jd_digest() -> dict[str, Any]:
    """The personal-corpus digest from scripts/build_user_corpus.py, if it has
    ever been run. Absent (no postings added yet) -> {}, and every function below
    degrades to exactly today's behaviour."""
    if not JD_DIGEST_PATH.exists():
        return {}
    return json.loads(JD_DIGEST_PATH.read_text(encoding="utf-8"))


def dimension_multiplier(rule_id: str) -> float:
    dimension = RULE_DIMENSION.get(rule_id)
    digest = jd_digest()
    if not dimension or not digest:
        return 1.0
    entry = digest.get("dimensions", {}).get(dimension)
    if not entry or not entry.get("total"):
        return 1.0
    share = entry["count"] / entry["total"]
    return 1.0 + (DIMENSION_MAX_MULTIPLIER - 1.0) * share


def target_titles() -> list[str]:
    return jd_digest().get("target_titles", [])


@functools.lru_cache(maxsize=1)
def load(path: str | None = None) -> dict[str, Any]:
    target = Path(path) if path else CONFIG_PATH
    with target.open("rb") as fh:
        return tomllib.load(fh)


def category_weights() -> dict[Category, float]:
    raw = load()["categories"]
    return {Category(name): float(value) for name, value in raw.items()}


def severity_points() -> dict[Severity, float]:
    raw = load()["severity"]
    return {Severity(name): float(value) for name, value in raw.items()}


def cap_for(provenance: Provenance) -> Severity | None:
    """Heuristic rules cannot exceed the capped severity, whatever they declare."""
    caps = load().get("provenance_caps", {})
    name = caps.get(provenance.value)
    return Severity(name) if name else None


def apply_provenance_cap(severity: Severity, provenance: Provenance) -> Severity:
    cap = cap_for(provenance)
    if cap is None:
        return severity
    return cap if SEVERITY_ORDER[severity] > SEVERITY_ORDER[cap] else severity


def ensemble_settings(mode: str | None = None) -> dict[str, Any]:
    """Merge the base [ensemble] block with the named mode's overrides."""
    block = dict(load()["ensemble"])
    chosen = mode or block.get("mode", "default")
    overrides = block.pop("economy", {}), block.pop("thorough", {})
    by_name = {"economy": overrides[0], "thorough": overrides[1]}
    block.update(by_name.get(chosen, {}))
    block["mode"] = chosen
    return block


def scoring() -> dict[str, Any]:
    return load()["scoring"]
