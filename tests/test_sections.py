"""Section segmentation and date arithmetic."""
from datetime import date
from pathlib import Path

import pytest

from ats.passes import resolvable_locators
from ats.prompts import places
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


SYNTHETIC = Path(__file__).resolve().parents[1] / "corpus" / "resumes" / "synthetic"


@pytest.mark.parametrize("prefix,headline", [
    ("07", "Data engineer, analytics platform."),
    ("10", "New graduate, agentic systems."),
    ("11", "Agentic AI engineer."),
    ("23", "GenAI product engineer."),
    ("30", "GenAI product engineer, two years."),
])
def test_the_headline_above_the_first_role_is_a_citable_place(prefix, headline):
    """The line under the contact details is what Luna refused to cite on 27 September."""
    resume = parse(next(SYNTHETIC.glob(f"{prefix}-*.txt")).read_text(encoding="utf-8"))
    assert resume.summary == headline
    assert "summary" in resolvable_locators(resume)
    assert f"summary: {headline}" in places(resume)


def test_a_header_with_only_a_name_and_contact_details_has_no_headline():
    resume = parse(RESUME.replace("SUMMARY\nAI Engineer, 3 years. LLM serving and evaluation.\n", ""))
    assert resume.summary == ""


def test_a_wrapped_bullet_line_starting_with_a_capital_or_digit_stays_in_the_bullet():
    """PDF text keeps no indent, so "Grafana, 14 dashboards." once opened a fake role."""
    resume = parse("""Riley Tang
riley@example.com

EXPERIENCE
Engineer, Meridian Energy Retail    Jan 2022 - Mar 2025
• Drift and cost were monitored in
Grafana, 14 dashboards.
• Improved retrieval,
19% fewer failed reviews.

VOLUNTEERING
Coach, junior robotics league.
""")
    assert len(resume.roles) == 1
    assert [text for _, text in resume.bullets] == [
        "Drift and cost were monitored in Grafana, 14 dashboards.",
        "Improved retrieval, 19% fewer failed reviews."]


JOB = """Riley Tang
riley@example.com

EXPERIENCE
AI Engineer, Northwind Data    Mar 2024 - Present
• Shipped the fraud service.
"""


def test_a_heading_split_over_two_lines_opens_one_role_and_leaves_the_bullet_alone():
    resume = parse(JOB + "Corvus Labs\nML Engineer    Jan 2022 - Jun 2023\n• Built the eval harness.\n")
    assert [text for _, text in resume.bullets] == ["Shipped the fraud service.",
                                                   "Built the eval harness."]
    assert [(r.title, r.company) for r in resume.roles][1] == ("ML Engineer", "Corvus Labs")


def test_undated_project_names_open_projects_of_their_own():
    resume = parse(JOB + "\nPROJECTS\nPond\n• A tiny job queue in Go.\nLedger\n"
                         "• An audit-log reader for agent runs.\n")
    assert [(r.heading, r.bullets) for r in resume.roles[1:]] == [
        ("Pond", ["A tiny job queue in Go."]),
        ("Ledger", ["An audit-log reader for agent runs."])]
    assert resume.roles[0].bullets == ["Shipped the fraud service."]


def test_project_bullets_with_no_name_are_not_filed_under_the_last_job():
    resume = parse(JOB + "\nPROJECTS\n• A KV-cache sizing calculator.\n")
    assert [(r.heading, r.bullets) for r in resume.roles] == [
        ("AI Engineer, Northwind Data    Mar 2024 - Present", ["Shipped the fraud service."]),
        ("Projects", ["A KV-cache sizing calculator."])]


def test_an_unknown_title_case_heading_is_not_glued_into_a_bullet():
    resume = parse(JOB + "Open Source Contributions\n• Fixed a vLLM scheduler bug.\n")
    assert resume.roles[0].bullets == ["Shipped the fraud service."]
    assert resume.roles[1].heading == "Open Source Contributions"


@pytest.mark.parametrize("header,headline", [
    ("Riley Tang\nriley@example.com\nLondon, United Kingdom\nAgentic AI engineer.", "Agentic AI engineer."),
    ("Riley Tang\nriley@example.com\nRemote / open to relocation\nAgentic AI engineer.", "Agentic AI engineer."),
    ("riley@example.com | (415) 555-0142\nRiley Tang\nAgentic AI engineer.", "Agentic AI engineer."),
    ("Riley Tang\nriley@example.com\nAgentic AI engineer.\nOpen to hybrid work.", "Agentic AI engineer."),
])
def test_the_headline_is_one_line_and_never_a_name_or_a_place(header, headline):
    assert parse(header + "\n\nEXPERIENCE\nAI Engineer, Northwind Data    Mar 2024 - Present\n"
                          "• Shipped it.\n").summary == headline


def test_a_career_block_under_an_unknown_heading_is_not_a_headline():
    text = ("Riley Tang\nriley@example.com\n\nCAREER HISTORY\n"
            "AI Engineer, Northwind Data    Mar 2024 - Present\n• Shipped it.\n\nSKILLS\nPython\n")
    assert parse(text).summary == ""
