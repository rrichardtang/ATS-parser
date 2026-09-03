"""Section segmentation and date arithmetic."""
from datetime import date

import pytest

from ats.sections import parse, parse_date_range

RESUME = """Riley Tang
riley@example.com | (415) 555-0142 | github.com/rileytang | Seattle, WA

SUMMARY
AI Engineer, 3 years. LLM serving and evaluation.

EXPERIENCE
AI Engineer, Northwind Data                        Mar 2024 - Present
• Cut p99 latency 380ms to 95ms with vLLM.
• Built the eval harness for our RAG pipeline.

ML Engineer, Corvus Labs                           Jan 2022 - Jun 2023
• Shipped a LoRA fine-tune of Mistral-7B.

SKILLS
Python, PyTorch, vLLM
"""


@pytest.mark.parametrize("text,start,current", [
    ("Mar 2024 - Present", date(2024, 3, 1), True),
    ("01/2023-04/2024", date(2023, 1, 1), False),
    ("2021 to present", date(2021, 1, 1), True),
    ("Jan 2022 – Jun 2023", date(2022, 1, 1), False),
])
def test_date_ranges(text, start, current):
    parsed = parse_date_range(text)
    assert parsed is not None
    assert parsed[0] == start
    assert parsed[2] is current


def test_sections_and_contact():
    r = parse(RESUME)
    assert set(r.section_order) >= {"summary", "experience", "skills"}
    assert r.contact.email == "riley@example.com"
    assert r.contact.phone == "(415) 555-0142"
    assert r.contact.github == "github.com/rileytang"


def test_roles_and_bullets():
    r = parse(RESUME)
    assert len(r.roles) == 2
    assert r.roles[0].title == "AI Engineer"
    assert r.roles[0].company == "Northwind Data"
    assert len(r.bullets) == 3
    assert r.bullets[0][0] == "exp[0].bullet[0]"


def test_gap_detection():
    """Overlapping roles must not double-count; a real gap must be found."""
    r = parse(RESUME)
    gaps = r.gaps(6)
    assert len(gaps) == 1
    assert gaps[0][0] == date(2023, 6, 1)
