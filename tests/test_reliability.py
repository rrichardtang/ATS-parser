"""Krippendorff's alpha, pinned to the maths rather than to a library.

The expected coefficients below were derived by hand from the definition -- the
coincidence matrix, then D_o and D_e -- so a change to the implementation that
happens to keep some other implementation happy still fails here.
"""
import pytest

from ats.reliability import Alpha, alpha


# Three observers, twelve units, missing judgements throughout -- the shape the
# harness actually sees when a provider errors on one resume. Expected values are
# hand-derived from the definition (D_o and D_e over the coincidence matrix), not
# copied from a library, so this pins the implementation to the maths.
CANONICAL = [
    [v for v in column if v is not None]
    for column in zip(
        [None, None, None, None, None, 3, 4, 1, 2, 1, 1, 3],
        [1, None, 2, 1, 3, 3, 4, 3, None, None, None, None],
        [None, None, 2, 1, 3, 4, 4, None, 2, 1, 1, 3],
    )
]


@pytest.mark.parametrize("level,expected", [
    ("nominal", 0.76),
    ("ordinal", 0.82),
    ("interval", 0.82),
])
def test_alpha_matches_the_hand_computed_coefficient(level, expected):
    assert alpha(CANONICAL, level=level).value == pytest.approx(expected, abs=0.005)


def test_alpha_drops_units_nobody_judged_twice():
    """A provider erroring on one resume costs that resume, not the run."""
    result = alpha([[1, 3], [2], [], [2, 2]], level="interval")
    assert result.units == 2


def test_perfect_agreement_is_one_but_no_variance_is_not():
    """The coincidence ticket 08 warned about must not read as a pass.

    Judges landing on the same value for every resume have agreed about nothing:
    there is no variance for the rubric to have explained. Reporting 1.00 there
    would be exactly the false pass the chance correction exists to catch.
    """
    assert alpha([[70, 70], [40, 40], [90, 90]], "interval").value == 1.0
    flat = alpha([[70, 70], [70, 70], [70, 70]], "interval")
    assert flat.value is None
    assert "nothing to agree about" in flat.note


def test_systematic_opposition_scores_below_zero():
    assert alpha([[1, 3], [3, 1], [1, 3], [3, 1]], "interval").value < 0


def test_ordinal_ranks_bands_by_the_declared_order():
    """Without --bands there is nothing to rank by, so adjacency is unknowable."""
    units = [["thin", "solid"], ["solid", "solid"], ["absent", "strong"], ["thin", "thin"]]
    ordered = alpha(units, "ordinal", order=["absent", "thin", "solid", "strong"])
    assert ordered.value is not None
    assert ordered.value != alpha(units, "nominal").value


def test_alpha_str_shows_absence_rather_than_a_number():
    assert str(Alpha(None, 0, "why")) == "n/a"
    assert str(Alpha(0.3123, 8)) == "0.31"
