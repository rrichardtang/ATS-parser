import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests.make_fixtures import build_all  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def fixtures():
    """Fixture PDFs are generated, not checked in, so the inputs stay reviewable."""
    return build_all()


@pytest.fixture(scope="session")
def analyzed(fixtures):
    from ats.pipeline import RunInput, analyze

    return {name: analyze(RunInput(pdf_path=str(path))) for name, path in fixtures.items()}
