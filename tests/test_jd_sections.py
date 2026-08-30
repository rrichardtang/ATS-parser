"""The JD section classifier: header detection, then the header-free sentence
fallback, then the safe "treat it all as required" default when neither fires.
"""
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
