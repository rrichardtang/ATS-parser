"""Generates the PDFs the extraction tests run against.

Kept as a script rather than binary fixtures so the inputs stay readable and
reviewable in the diff.
"""
from __future__ import annotations

from pathlib import Path

from reportlab.lib.colors import Color, black
from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas

OUT = Path(__file__).parent / "fixtures"
WIDTH, HEIGHT = LETTER

STRONG_BULLETS = [
    "Cut p99 inference latency 380ms to 95ms by moving Llama-3-8B to vLLM with",
    "  continuous batching, holding 1.2k req/min on 4 A10Gs.",
    "Owned the eval harness for our RAG pipeline: 900 labelled QA pairs, and raised",
    "  answer-groundedness from 71% to 88% over six weeks by fixing chunk overlap",
    "  and adding a reranker.",
    "Shipped a LoRA fine-tune of Mistral-7B for ticket triage, +11 pts exact match.",
    "Cut GPU spend 34% ($18k/mo) by profiling the serving path and replacing padded",
    "  batching with length-bucketed batching.",
]

SECOND_ROLE_BULLETS = [
    "Replaced a nightly Airflow batch job with a streaming feature pipeline, cutting",
    "  feature staleness from 18 hours to 4 minutes for 2.3M user rows.",
    "Wrote the retraining loop and drift monitor that caught a 9-point AUC regression",
    "  before it reached production.",
    "Ported model serving from Flask to FastAPI with async batching; throughput went",
    "  from 40 to 310 requests per second on the same hardware.",
]

SLOP_BULLETS = [
    "Leveraged cutting-edge AI technologies to deliver robust and scalable",
    "  solutions, showcasing my commitment to excellence.",
    "Responsible for utilizing machine learning frameworks to facilitate",
    "  data-driven insights, underscoring the value of innovation.",
    "Helped the team to streamline various processes, highlighting my ability",
    "  to empower cross-functional stakeholders.",
    "Worked on delving into transformative model architectures, elevating our",
    "  paradigm shift toward ever-evolving intelligent systems.",
]


def _header(c, name="Riley Tang", phone=True):
    c.setFont("Helvetica-Bold", 18)
    c.drawString(72, HEIGHT - 72, name)
    c.setFont("Helvetica", 9)
    bits = ["riley.tang@example.com"]
    if phone:
        bits.append("(415) 555-0142")
    bits += ["linkedin.com/in/rileytang", "github.com/rileytang", "Seattle, WA"]
    c.drawString(72, HEIGHT - 88, "  |  ".join(bits))


def _section(c, y, title):
    c.setFont("Helvetica-Bold", 11)
    c.drawString(72, y, title.upper())
    c.setLineWidth(0.5)
    c.line(72, y - 4, WIDTH - 72, y - 4)
    return y - 20


def strong(path: Path):
    c = canvas.Canvas(str(path), pagesize=LETTER)
    _header(c)
    y = _section(c, HEIGHT - 120, "Summary")
    c.setFont("Helvetica", 9.5)
    c.drawString(72, y, "AI Engineer, 3 years. LLM serving, evaluation, and RAG systems in production.")
    y = _section(c, y - 28, "Experience")
    for role, dates, body in [
        ("AI Engineer, Northwind Data", "Mar 2024 - Present", STRONG_BULLETS),
        ("ML Engineer, Corvus Labs", "Aug 2022 - Feb 2024", SECOND_ROLE_BULLETS),
    ]:
        c.setFont("Helvetica-Bold", 10)
        c.drawString(72, y, role)
        c.setFont("Helvetica", 9)
        c.drawRightString(WIDTH - 72, y, dates)
        y -= 15
        c.setFont("Helvetica", 9.5)
        for line in body:
            prefix = "\u2022 " if not line.startswith("  ") else "   "
            c.drawString(80, y, prefix + line.strip())
            y -= 13
        y -= 8
    y = _section(c, y, "Skills")
    c.setFont("Helvetica", 9.5)
    c.drawString(72, y, "Python, PyTorch, vLLM, FastAPI, Docker, Kubernetes, Postgres/pgvector, Weights & Biases")
    y = _section(c, y - 24, "Education")
    c.setFont("Helvetica", 9.5)
    c.drawString(72, y, "B.S. Computer Science, University of Washington, 2022")
    c.save()


def slop(path: Path):
    c = canvas.Canvas(str(path), pagesize=LETTER)
    _header(c)
    y = _section(c, HEIGHT - 120, "Summary")
    c.setFont("Helvetica", 9.5)
    c.drawString(72, y, "It's not just about code. It's about impact. A passionate engineer who delves")
    c.drawString(72, y - 12, "into the realm of AI, leveraging cutting-edge tools to empower teams.")
    y = _section(c, y - 40, "Experience")
    for role, dates in [("Software Engineer II, Northwind Data", "Mar 2024 - Present"),
                        ("Junior Developer, Corvus Labs", "Aug 2022 - Feb 2024")]:
        c.setFont("Helvetica-Bold", 10)
        c.drawString(72, y, role)
        c.setFont("Helvetica", 9)
        c.drawRightString(WIDTH - 72, y, dates)
        y -= 15
        c.setFont("Helvetica", 9.5)
        for line in SLOP_BULLETS:
            prefix = "• " if not line.startswith("  ") else "   "
            c.drawString(80, y, prefix + line.strip())
            y -= 13
        y -= 8
    y = _section(c, y, "Skills")
    c.setFont("Helvetica", 9.5)
    c.drawString(72, y, "Python, Java, C++, SQL, AI, ML, LLM, RAG, PyTorch, TensorFlow, Docker, K8s, AWS,")
    c.drawString(72, y - 12, "GCP, Azure, leadership, communication, teamwork, problem-solving, agile, Scrum")
    c.save()


def two_column(path: Path):
    c = canvas.Canvas(str(path), pagesize=LETTER)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(60, HEIGHT - 60, "Riley Tang")
    left_x, right_x = 60, 340
    y = HEIGHT - 110
    c.setFont("Helvetica", 9)
    for line in ["SKILLS", "Python", "PyTorch", "vLLM", "FastAPI", "Docker",
                 "Kubernetes", "Postgres", "pgvector", "Airflow", "Spark"]:
        c.drawString(left_x, y, line)
        y -= 14
    y = HEIGHT - 110
    for line in ["EXPERIENCE", "AI Engineer, Northwind Data", "Mar 2024 - Present",
                 "Cut p99 latency 380ms to 95ms with", "vLLM continuous batching.",
                 "Built eval harness, 71% to 88%", "groundedness on 900 QA pairs.",
                 "ML Engineer, Corvus Labs", "Aug 2022 - Feb 2024",
                 "Shipped LoRA fine-tune, +11 pts", "exact match on ticket triage."]:
        c.drawString(right_x, y, line)
        y -= 14
    c.save()


def hidden_text(path: Path):
    c = canvas.Canvas(str(path), pagesize=LETTER)
    _header(c)
    y = _section(c, HEIGHT - 120, "Experience")
    c.setFont("Helvetica", 9.5)
    c.drawString(72, y, "• Built and shipped an LLM serving path on vLLM, 380ms to 95ms p99.")
    # White-on-white keyword injection, the thing an ATS flags as fraud.
    c.setFillColor(Color(1, 1, 1))
    c.drawString(72, y - 40, "machine learning expert senior staff principal AI researcher PhD")
    c.setFillColor(black)
    c.save()


def scanned(path: Path):
    """A page with no text layer at all -- drawn as vector strokes."""
    c = canvas.Canvas(str(path), pagesize=LETTER)
    c.setLineWidth(2)
    for i in range(18):
        y = HEIGHT - 100 - i * 22
        c.line(72, y, 72 + 380 - (i % 5) * 40, y)
    c.save()


def no_phone(path: Path):
    """Identical to the strong resume but without a phone number."""
    c = canvas.Canvas(str(path), pagesize=LETTER)
    _header(c, phone=False)
    y = _section(c, HEIGHT - 120, "Summary")
    c.setFont("Helvetica", 9.5)
    c.drawString(72, y, "AI Engineer, 3 years. LLM serving, evaluation, and RAG systems in production.")
    y = _section(c, y - 28, "Experience")
    c.setFont("Helvetica-Bold", 10)
    c.drawString(72, y, "AI Engineer, Northwind Data")
    c.setFont("Helvetica", 9)
    c.drawRightString(WIDTH - 72, y, "Mar 2024 - Present")
    y -= 15
    c.setFont("Helvetica", 9.5)
    for line in STRONG_BULLETS:
        prefix = "• " if not line.startswith("  ") else "   "
        c.drawString(80, y, prefix + line.strip())
        y -= 13
    c.setFont("Helvetica-Bold", 10)
    c.drawString(72, y - 8, "ML Engineer, Corvus Labs")
    c.setFont("Helvetica", 9)
    c.drawRightString(WIDTH - 72, y - 8, "Aug 2022 - Feb 2024")
    y -= 23
    c.setFont("Helvetica", 9.5)
    for line in SECOND_ROLE_BULLETS:
        prefix = "\u2022 " if not line.startswith("  ") else "   "
        c.drawString(80, y, prefix + line.strip())
        y -= 13
    y = _section(c, y - 10, "Skills")
    c.setFont("Helvetica", 9.5)
    c.drawString(72, y, "Python, PyTorch, vLLM, FastAPI, Docker, Kubernetes, pgvector")
    y = _section(c, y - 24, "Education")
    c.setFont("Helvetica", 9.5)
    c.drawString(72, y, "B.S. Computer Science, University of Washington, 2022")
    c.save()


def buried_evidence(path: Path):
    """Parses cleanly, but nothing identifying reaches the top third of page 1."""
    c = canvas.Canvas(str(path), pagesize=LETTER)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(72, HEIGHT - 60, "Riley Tang")
    c.setFont("Helvetica", 9)
    c.drawString(72, HEIGHT - 76, "riley.tang@example.com | (415) 555-0142")
    y = _section(c, HEIGHT - 110, "Interests")
    c.setFont("Helvetica", 9.5)
    for line in ["Long-distance cycling and randonneuring.", "Amateur radio (call sign KJ7ABC).",
                 "Volunteer mentor, local robotics club.", "Reading about urban planning.",
                 "Backcountry skiing.", "Chess, rated 1650 USCF.",
                 "Home automation projects.", "Woodworking, mostly hand tools."]:
        c.drawString(72, y, "• " + line)
        y -= 14
    y = _section(c, y - 20, "Education")
    c.setFont("Helvetica", 9.5)
    c.drawString(72, y, "B.S. Computer Science, University of Washington, 2021")
    y = _section(c, y - 30, "Experience")
    c.setFont("Helvetica-Bold", 10)
    c.drawString(72, y, "AI Engineer, Northwind Data")
    c.setFont("Helvetica", 9)
    c.drawRightString(WIDTH - 72, y, "Mar 2024 - Present")
    y -= 15
    c.setFont("Helvetica", 9.5)
    for line in STRONG_BULLETS:
        prefix = "• " if not line.startswith("  ") else "   "
        c.drawString(80, y, prefix + line.strip())
        y -= 13
    c.save()


def build_all() -> dict[str, Path]:
    OUT.mkdir(parents=True, exist_ok=True)
    made = {}
    for name, fn in [("strong", strong), ("slop", slop), ("two_column", two_column),
                     ("hidden_text", hidden_text), ("scanned", scanned),
                     ("no_phone", no_phone), ("buried_evidence", buried_evidence)]:
        path = OUT / f"{name}.pdf"
        fn(path)
        made[name] = path
    return made


if __name__ == "__main__":
    for name, path in build_all().items():
        print(f"{name}: {path}")
