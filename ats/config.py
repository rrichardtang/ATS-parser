"""Loads weights.toml. Every tunable number lives there, not scattered in code."""
from __future__ import annotations

import functools
import json
import tomllib
from pathlib import Path
from typing import Any

from .models import DERIVED_CATEGORIES, Category, Provenance, Severity

CONFIG_PATH = Path(__file__).with_name("weights.toml")
JD_DIGEST_PATH = Path(__file__).with_name("jd_digest.json")

SEVERITY_ORDER = {Severity.MINOR: 0, Severity.MAJOR: 1, Severity.CRITICAL: 2}

# Which existing rule a JD-derived dimension amplifies. Never a new rubric axis --
# only ever scales how much an already-judged rule costs, for this user's runs.
# See ats/jd_dimensions.py for what each dimension detects and why cross-functional
# collaboration isn't wired in here.
#
# Ticket 04 removed four entries -- content/ownership, cred/no-production,
# cred/notebook-only, cred/no-evaluation -- because their categories' weights are now
# derived from the same document frequency this multiplier reads. Spending one count
# twice, once on the weight and once on the rule's cost, is the double count 03 closed
# arriving one layer down. title/seniority-mismatch survives because its category
# (Title & seniority alignment) keeps an authored weight, so nothing else spends the
# seniority count.
RULE_DIMENSION = {
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


def derived_document_frequency() -> tuple[dict[str, int], int]:
    """How many target postings state each derived category's behaviour, and how many
    postings there were.

    The live digest when one has been built, and `weights.toml`'s recorded fallback
    when it has not -- the same six-posting scan the repo ships `jd_digest.json` for.
    A fresh checkout with no personal corpus therefore scores by the corpus it shipped
    with, rather than by a derived block silently collapsing to zero.
    """
    entries = jd_digest().get("category_document_frequency") or {}
    names = [c.value for c in DERIVED_CATEGORIES]
    if all(name in entries and entries[name].get("total") for name in names):
        return ({name: int(entries[name]["count"]) for name in names},
                int(max(entries[name]["total"] for name in names)))
    recorded = load()["derived"]["fallback_document_frequency"]
    return ({name: int(recorded[name]) for name in names}, int(recorded["postings"]))


def category_weights() -> dict[Category, float]:
    """Every category's weight, authored block and derived block together.

    The authored four are read from `weights.toml`. The derived four are computed --
    `weights.toml` deliberately holds no number for them, only the budget they share
    (50, set by the migration map's 02) -- so a category's weight follows the corpus
    and cannot be edited out of step with it.

    Ordered by `Category`, not by either source, because this dict's order is the
    order the report prints its categories in.
    """
    from .jd_dimensions import derived_weights

    authored = {Category(name): float(value)
                for name, value in load()["categories"].items()}
    counts, postings = derived_document_frequency()
    budget = float(load()["derived"]["budget"])
    derived = {Category(name): value
               for name, value in derived_weights(counts, postings, budget).items()}
    combined = authored | derived
    missing = [c for c in Category if c not in combined]
    if missing:
        raise SystemExit(f"weights.toml gives no weight for {[c.value for c in missing]}")
    return {category: combined[category] for category in Category}


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
