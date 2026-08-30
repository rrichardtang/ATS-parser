"""The JD section classifier: header detection, the rescue pass when headers were
found but none of them was a requirements header, then the header-free sentence
fallback, then the safe "treat it all as required" default when none of them fires.
"""
import pytest

from ats.jd_sections import NICE, OTHER, REQUIRED, RESPONSIBILITIES, classify

HEADERED = """
About Example Corp
We build things people like.

About the Role
You will design and ship machine learning systems end to end.
You will partner with product on roadmap.

What We're Looking For
3+ years of experience with PyTorch.
Strong SQL skills.

Nice to Have
Experience with Kubernetes.

Benefits
Health insurance and 401k.
"""

HEADERLESS = (
    "You'll build and ship ML systems that serve real users. "
    "You will also help design the roadmap. "
    "You have 3+ years of experience with PyTorch and strong SQL skills. "
    "Experience with Kubernetes is required."
)

UNCLASSIFIABLE = "We are a fast-growing company doing interesting things in the space."


def test_headers_route_lines_to_the_right_bucket():
    spans = classify(HEADERED)
    assert "pytorch" in spans[REQUIRED].lower()
    assert "sql" in spans[REQUIRED].lower()
    assert "kubernetes" in spans[NICE].lower()
    assert "design and ship" in spans[RESPONSIBILITIES].lower()
    assert "401k" in spans[OTHER].lower()
    # A responsibilities-section mention must not leak into required.
    assert "design and ship" not in spans[REQUIRED].lower()


def test_sentence_fallback_used_only_when_no_headers_found():
    spans = classify(HEADERLESS)
    assert "pytorch" in spans[REQUIRED].lower()
    assert "kubernetes" in spans[REQUIRED].lower()
    assert "build and ship" in spans[RESPONSIBILITIES].lower()


def test_content_before_the_first_header_is_kept_not_dropped():
    """An unlabeled opening paragraph is exactly where ownership/scope language
    tends to live -- treating it as responsibilities keeps it visible to
    dimension detection without letting it inflate required-skill counts."""
    text = "Own production ML systems end to end.\n\nRequirements\n3+ years with PyTorch.\n"
    spans = classify(text)
    assert "own production" in spans[RESPONSIBILITIES].lower()
    assert "pytorch" in spans[REQUIRED].lower()
    assert "own production" not in spans[REQUIRED].lower()


def test_unclassifiable_text_falls_back_to_required_not_dropped():
    """Losing a posting's signal entirely would be worse than the old flat
    behaviour -- so with no signal at all, everything counts as required, exactly
    like a plain, undifferentiated blob did before section-awareness existed."""
    spans = classify(UNCLASSIFIABLE)
    assert spans[REQUIRED] == UNCLASSIFIABLE
    assert spans[NICE] == spans[RESPONSIBILITIES] == spans[OTHER] == ""


# Every header below is copied verbatim from a posting in corpus/jds/user/ --
# including its apostrophe glyph, which is the point: the same header reaches this
# code spelled two different ways depending on which careers site it came from.
REAL_POSTING_HEADERS = [
    # Anthropic and OpenAI both introduce their requirements list as a
    # conditional sentence rather than a noun heading.
    (REQUIRED, "You May Be a Good Fit If You Have"),
    (REQUIRED, "You Might Be a Good Fit If You"),
    (REQUIRED, "What You Need"),
    (REQUIRED, "What We’re Looking For"),
    (REQUIRED, "What We're Looking For"),
    (REQUIRED, "Qualifications"),
    (RESPONSIBILITIES, "What You’ll Do"),
    (RESPONSIBILITIES, "What You'll Do"),
    (RESPONSIBILITIES, "About The Role"),
    (RESPONSIBILITIES, "Responsibilities"),
    (RESPONSIBILITIES, "Role Scope"),
    (NICE, "Bonus Points"),
    (NICE, "Preferred Qualifications"),
    # A stack listing, prefaced in the posting with "we don't hire to a narrow
    # checklist" -- relevant tools, but not stated requirements.
    (NICE, "Technical Environment"),
]


def _posting(header: str) -> str:
    """The header under test, given a requirements section it does not own so the
    rescue pass stays out of the way of what is being measured."""
    return f"Requirements\n* 5+ years of Python.\n\n{header}\n* Kubernetes and Terraform.\n"


@pytest.mark.parametrize(
    "bucket,header", REAL_POSTING_HEADERS, ids=[h for _, h in REAL_POSTING_HEADERS]
)
def test_real_posting_headers_route_their_section_to_one_bucket(bucket, header):
    spans = classify(_posting(header))
    lands_in = [b for b in (REQUIRED, NICE, RESPONSIBILITIES, OTHER)
                if "kubernetes" in spans[b].lower()]
    assert lands_in == [bucket]


@pytest.mark.parametrize(
    "header", ["What We{}re Looking For", "What You{}ll Do", "You Might Be a Good Fit If You{}d"]
)
def test_typographic_apostrophe_reads_the_same_as_its_ascii_twin(header):
    """Copy-paste from a careers site carries U+2019, not an ASCII apostrophe --
    and the corpus holds both spellings of the same header, from two postings. A
    vocabulary written with ' silently skipped the typographic half."""
    assert classify(_posting(header.format("’"))) == classify(_posting(header.format("'")))


def test_requirements_rescue_when_no_header_matched_the_requirements_section():
    """A posting whose requirements heading isn't in the vocabulary drops that
    list into responsibilities, where it counts toward no skill at all -- and says
    nothing about it, because four spans still come back."""
    spans = classify(
        "About The Role\n"
        "You will ship agentic systems.\n"
        "\n"
        "Here Is What Would Make You Thrive\n"
        "* 4+ years of experience with Python.\n"
        "* You have shipped LLM systems to production.\n"
    )
    assert "python" in spans[REQUIRED].lower()
    assert "shipped llm systems" in spans[REQUIRED].lower()
    # The rescue moves rather than copies, so nothing is counted twice.
    assert "python" not in spans[RESPONSIBILITIES].lower()
    assert "you will ship agentic systems" in spans[RESPONSIBILITIES].lower()


def test_rescue_leaves_responsibilities_alone_once_a_requirements_header_matched():
    spans = classify(
        "What You’ll Do\n"
        "* Build eval harnesses, drawing on experience with Kubernetes.\n"
        "\n"
        "What You Need\n"
        "* Strong Python.\n"
    )
    assert "python" in spans[REQUIRED].lower()
    assert "kubernetes" in spans[RESPONSIBILITIES].lower()
    assert "kubernetes" not in spans[REQUIRED].lower()
