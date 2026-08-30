"""scripts/build_user_corpus.py's build() logic, against temp fixture postings --
never the real corpus/jds/user/ or ats/taxonomy.json, so running the suite can
never corrupt either.
"""
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

_spec = importlib.util.spec_from_file_location(
    "build_user_corpus", ROOT / "scripts" / "build_user_corpus.py"
)
build_user_corpus = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(build_user_corpus)

POSTING_A = {
    "title": "AI Engineer",
    "company": "Alpha",
    "source_url": "https://alpha.example/careers/1",
    "date_added": "2026-08-01",
    "raw_text": (
        "About the Role\n"
        "Own production ML systems end to end.\n\n"
        "What We're Looking For\n"
        "3+ years with PyTorch. Strong evaluation methodology.\n\n"
        "Nice to Have\n"
        "Experience with Kubernetes.\n"
    ),
}
POSTING_B = {
    "title": "Applied AI Engineer",
    "company": "Beta",
    "source_url": "https://beta.example/careers/2",
    "date_added": "2026-08-05",
    "raw_text": (
        "About the Role\n"
        "You'll own the full lifecycle of our recommendation systems.\n\n"
        "Requirements\n"
        "PyTorch experience required. Rigorous evals before every launch.\n"
    ),
}


def _write(tmp_path, postings):
    for i, posting in enumerate(postings):
        (tmp_path / f"posting-{i}.json").write_text(json.dumps(posting), encoding="utf-8")
    return tmp_path


def test_empty_corpus_is_a_no_op(tmp_path):
    assert build_user_corpus.build(tmp_path) is None


def test_required_term_frequency_and_dimension_counts(tmp_path):
    _write(tmp_path, [POSTING_A, POSTING_B])
    result = build_user_corpus.build(tmp_path)
    assert result is not None

    taxonomy, digest = result["taxonomy"], result["digest"]
    assert taxonomy["document_count"] == 2
    assert digest["document_count"] == 2
    assert sorted(digest["target_titles"]) == ["AI Engineer", "Applied AI Engineer"]

    pytorch = taxonomy["terms"]["core_ml/pytorch"]
    assert pytorch["required_doc_frequency"] == 2  # both postings require it
    assert pytorch["weight"] == 1.0
    assert pytorch["provenance"] == "jd-derived"

    kubernetes = taxonomy["terms"]["serving/kubernetes"]
    assert kubernetes["required_doc_frequency"] == 0
    assert kubernetes["nice_doc_frequency"] == 1  # only posting A, and only nice-to-have
    assert 0 < kubernetes["weight"] < pytorch["weight"]

    # Both postings ask for evaluation rigor -- 5/5-style dimension, not a keyword.
    assert digest["dimensions"]["ownership"]["count"] == 2
    assert digest["dimensions"]["evaluation"]["count"] == 2
    assert digest["dimensions"]["ai_assisted_coding"]["count"] == 0

    # And the behaviour counts 04 derives category weight from, which are per
    # category rather than per dimension.
    behaviours = digest["category_document_frequency"]
    assert behaviours["Evaluation rigour"] == {"count": 2, "total": 2}
    assert behaviours["AI-assisted coding fluency"] == {"count": 0, "total": 2}

    required_terms = {e["term"] for e in digest["required"]}
    assert "core_ml/pytorch" in required_terms
