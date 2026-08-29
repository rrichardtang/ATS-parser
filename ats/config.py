"""Loads weights.toml. Every tunable number lives there, not scattered in code."""
from __future__ import annotations

import functools
import tomllib
from pathlib import Path
from typing import Any

from .models import Category, Provenance, Severity

CONFIG_PATH = Path(__file__).with_name("weights.toml")

SEVERITY_ORDER = {Severity.MINOR: 0, Severity.MAJOR: 1, Severity.CRITICAL: 2}


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
