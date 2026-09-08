"""The acceptance set's own invariants: 08's rules, asserted rather than remembered.

What is tested here is provenance and coverage, not scoring. A number this set
produces is 09's; what this suite defends is that the set is still the set the numbers
were measured on, and that it has not quietly acquired the defect it was built to fix.
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ats.rubric import SLUGS, load_spec  # noqa: E402
from ats.sections import parse  # noqa: E402
from scripts import acceptance_coverage as coverage  # noqa: E402
from scripts import draw_briefs, make_acceptance_set  # noqa: E402
from scripts.criteria_probe import deterministic_verdict, read_probe  # noqa: E402

SET_DIR = ROOT / "corpus" / "resumes" / "synthetic"
MANIFEST = ROOT / "corpus" / "resumes" / "manifest.json"
BRIEFS = ROOT / "corpus" / "resumes" / "briefs.json"

# 08's floor: 30 documents give each category 30 paired band judgements and 150 paired
# criterion judgements per provider, against 29 probes whose judges also wrote them.
MINIMUM = 30


@pytest.fixture(scope="module")
def documents() -> dict[str, Path]:
    return {p.stem: p for p in sorted(SET_DIR.glob("*.txt"))}


@pytest.fixture(scope="module")
def docs(documents):
    return {name: read_probe(path) for name, path in documents.items()}


def test_the_set_is_at_least_the_stated_size(documents):
    assert len(documents) >= MINIMUM


def test_every_document_parses_to_roles_with_bullets(docs):
    for name, doc in docs.items():
        assert doc.answerable, f"{name}: {doc.note}"
        assert len(doc.resume.roles) >= 2, f"{name}: one role is not a career"
        bullets = [b for role in doc.resume.roles for b in role.bullets]
        assert len(bullets) >= 6, f"{name}: too few bullets to answer five criteria on"


def test_nothing_is_frozen_that_has_since_changed():
    assert make_acceptance_set.verify() == 0


def test_manifest_covers_every_document_and_names_its_brief(documents):
    recorded = json.loads(MANIFEST.read_text(encoding="utf-8"))
    briefs = {b["id"] for b in json.loads(BRIEFS.read_text(encoding="utf-8"))["briefs"]}
    entries = {e["id"]: e for e in recorded["documents"]}
    assert set(entries) == set(documents)
    for name, entry in entries.items():
        assert entry["brief"] in briefs, f"{name}: brief {entry['brief']} was never drawn"
        assert entry["provenance"] == "synthetic-from-brief"


def test_the_briefs_are_reproducible_from_their_seed():
    recorded = json.loads(BRIEFS.read_text(encoding="utf-8"))
    redrawn = draw_briefs.draw(recorded["count"], recorded["seed"])
    assert redrawn["briefs"] == recorded["briefs"]


def test_the_work_pool_still_comes_from_the_posting_corpus():
    """The provenance claim, checked rather than asserted in prose.

    If the postings change the digest moves, which is a real event -- the documents
    were written from the old draw -- and this is where it becomes visible.
    """
    recorded = json.loads(BRIEFS.read_text(encoding="utf-8"))
    pool = draw_briefs.work_pool()
    assert draw_briefs.pool_digest(pool) == recorded["work_pool"]["digest"]
    for item in pool:
        assert item["source"].startswith("corpus/jds/")


def test_no_document_carries_a_real_looking_contact(documents):
    """Tier 1 is invented, and this is the cheap half of keeping it that way."""
    for name, path in documents.items():
        text = path.read_text(encoding="utf-8")
        for email in re.findall(r"[\w.+-]+@[\w.-]+", text):
            assert email.endswith("@example.com"), f"{name}: {email}"
        for phone in re.findall(r"\(\d{3}\) (\d{3})-(\d{4})", text):
            assert phone[0] == "555" and phone[1].startswith("01"), f"{name}: {phone}"


def test_the_set_spreads_over_quality(documents):
    """A set where every resume is a strong AI engineer tests nothing, and neither does
    one where every resume is bad. The draw's own answer to that is `on_track`."""
    recorded = json.loads(MANIFEST.read_text(encoding="utf-8"))
    tracks = Counter(e["on_track"] for e in recorded["documents"])
    assert tracks[True] >= 5 and tracks[False] >= 5


def test_no_behaviour_criterion_is_constant_across_the_set(docs):
    """02's finding on the seven fixtures, as a standing test.

    `Agentic systems` and `AI-assisted coding fluency` were band E on all seven -- 60
    recorded answers, every one `no` -- so 22.5 of the composite's points carried no
    information. A test set that lets that back in is not a test set.
    """
    for slug in coverage.BEHAVIOUR:
        spec = load_spec(slug)
        met: Counter[str] = Counter()
        answered: Counter[str] = Counter()
        for doc in docs.values():
            verdict = deterministic_verdict(doc, spec)
            for cid, value in verdict.answers.items():
                answered[cid] += 1
                met[cid] += bool(value)
        for cid, seen in answered.items():
            assert 0 < met[cid] < seen, (
                f"{spec['category']}/{cid} is constant at "
                f"{'yes' if met[cid] else 'no'} over {seen} documents")


def test_resume_craft_still_has_the_two_constants_08_recorded(docs):
    """Recorded rather than fixed, and asserted so it cannot change unnoticed.

    C4 (`roles read differently`) and C5 (`could not be anyone's`) are constant on this
    set under the deterministic judge, and both predicates are length-sensitive: C5
    fails a document if *any* bullet is portable and C2 needs an outcome in *every*
    role, so a three-role resume is strictly harder than the two-role band probes the
    category was calibrated on. acceptance-set.md section 5 has the measurement. If
    this test fails, the finding it guards has changed -- go and read it.
    """
    spec = load_spec("resume-craft")
    answers = [deterministic_verdict(doc, spec).answers for doc in docs.values()]
    assert all(a["C4"] for a in answers)
    assert not any(a["C5"] for a in answers)


def test_every_document_renders_to_a_pdf_the_parser_reads(tmp_path, documents):
    from ats.extract import extract
    from ats.passes import withholding_reason

    for name, path in documents.items():
        out = tmp_path / f"{name}.pdf"
        make_acceptance_set.render(name, path.read_text(encoding="utf-8"), out)
        doc = extract(str(out))
        assert doc.has_text_layer, name
        assert not doc.multi_column_pages, f"{name}: rendered as multi-column"
        assert not doc.hidden_text, f"{name}: rendered with hidden text"
        resume = parse(doc.text)
        assert not withholding_reason(resume), name


def test_the_set_covers_every_category_the_rubric_has():
    assert set(SLUGS) == {
        "production-ownership", "agentic-systems", "evaluation-rigour",
        "ai-assisted-coding-fluency", "resume-craft",
    }
