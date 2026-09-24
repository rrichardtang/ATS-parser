"""Local web UI. One process: `uvicorn app:app`.

Uploads are analysed in a temp file and deleted immediately. API keys live in the
request only -- never written to disk, never logged, never stored in the cache key
in recoverable form.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import tempfile
import time
from pathlib import Path

from fastapi import FastAPI, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from ats.models import Gate, Report
from ats.pipeline import ExtractionError, RunInput, analyze, generate_rewrites, parse_resume
from ats.report import to_markdown, to_pdf
from ats.sections import Resume

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("ats.app")

ROOT = Path(__file__).parent
MAX_UPLOAD_BYTES = 12 * 1024 * 1024
CACHE_TTL_SECONDS = 3600
CACHE_LIMIT = 24

app = FastAPI(title="resume.diagnostics", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
templates = Jinja2Templates(directory=str(ROOT / "templates"))

# token -> (created_at, Report, Resume). Keeps export cheap, stops a re-render
# from re-running (or re-billing) the analysis, and holds onto the parsed bullet
# text so a later "Generate rewrites" click doesn't need the PDF again.
_CACHE: dict[str, tuple[float, Report, Resume]] = {}


def _cache_put(report: Report, resume: Resume, seed: str) -> str:
    _prune()
    token = hashlib.sha256(f"{seed}{time.time()}".encode()).hexdigest()[:16]
    _CACHE[token] = (time.time(), report, resume)
    return token


def _cache_get(token: str) -> tuple[Report, Resume] | None:
    _prune()
    entry = _CACHE.get(token)
    return (entry[1], entry[2]) if entry else None


def _cache_update(token: str, report: Report) -> None:
    entry = _CACHE.get(token)
    if entry:
        _CACHE[token] = (entry[0], report, entry[2])


def _prune() -> None:
    now = time.time()
    for key in [k for k, (t, _, _r) in _CACHE.items() if now - t > CACHE_TTL_SECONDS]:
        _CACHE.pop(key, None)
    while len(_CACHE) > CACHE_LIMIT:
        _CACHE.pop(min(_CACHE, key=lambda k: _CACHE[k][0]), None)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html", {})


def _mode(mode: str) -> str:
    return mode if mode in {"economy", "default", "thorough"} else "default"


@app.post("/analyze", response_class=HTMLResponse)
async def do_analyze(
    request: Request,
    pdf: UploadFile,
    jd: str = Form(""),
    anthropic_key: str = Form(""),
    openai_key: str = Form(""),
    mode: str = Form("default"),
):
    payload = await pdf.read()
    if not payload:
        return _error(request, "The upload was empty.")
    if len(payload) > MAX_UPLOAD_BYTES:
        return _error(request, f"File is larger than {MAX_UPLOAD_BYTES // (1024*1024)}MB.")
    if not payload.startswith(b"%PDF"):
        return _error(request, "That is not a PDF. Export your resume as PDF and retry.")

    handle, path = tempfile.mkstemp(suffix=".pdf")
    try:
        with os.fdopen(handle, "wb") as fh:
            fh.write(payload)
        run = RunInput(
            pdf_path=path,
            jd_text=jd or "",
            keys={"anthropic": anthropic_key.strip(), "openai": openai_key.strip()},
            ensemble_mode=_mode(mode),
            # Scoring never implies generating: rewrites are a separate, explicit
            # step the user triggers from the report -- see /generate below.
            enable_rewrites=False,
        )
        started = time.time()
        report = analyze(run)
        report.run_meta["elapsed_seconds"] = round(time.time() - started, 1)
        resume = parse_resume(path)
    except ExtractionError as exc:
        return _error(request, f"{exc}. If it is encrypted, remove the password and retry.")
    except Exception as exc:  # noqa: BLE001
        log.exception("analysis failed")
        return _error(request, f"Analysis failed: {exc}")
    finally:
        # The candidate's resume does not stay on disk.
        try:
            os.unlink(path)
        except OSError:
            pass

    token = _cache_put(report, resume, hashlib.sha256(payload).hexdigest())
    return _render(request, report, token)


@app.post("/generate/{token}", response_class=HTMLResponse)
async def do_generate(
    request: Request,
    token: str,
    anthropic_key: str = Form(""),
    openai_key: str = Form(""),
    mode: str = Form("default"),
):
    """Pass 3 alone, run only when the user asks for it -- see the button at the
    bottom of the report. Never fires as a side effect of scoring."""
    cached = _cache_get(token)
    if not cached:
        return _error(request, "This report has expired. Run the analysis again.")
    report, resume = cached

    try:
        report = generate_rewrites(
            report, resume,
            keys={"anthropic": anthropic_key.strip(), "openai": openai_key.strip()},
            models={}, ensemble_mode=_mode(mode),
        )
    except Exception as exc:  # noqa: BLE001
        log.exception("rewrite generation failed")
        return _error(request, f"Generating rewrites failed: {exc}")

    _cache_update(token, report)
    return _render(request, report, token)


def _render(request: Request, report: Report, token: str) -> HTMLResponse:
    return templates.TemplateResponse(request, "report.html", {
        "report": report,
        "token": token,
        "parser": report.grouped(Gate.PARSER),
        "recruiter": report.grouped(Gate.RECRUITER),
        "manager": report.grouped(Gate.MANAGER),
        "meta_json": json.dumps(report.run_meta, indent=2, default=str),
        "error": None,
    })


def _error(request: Request, message: str) -> HTMLResponse:
    return templates.TemplateResponse(
        request, "report.html",
        {"error": message, "report": None, "token": "",
         "parser": [], "recruiter": [], "manager": [], "meta_json": "{}"},
        status_code=200,
    )


@app.get("/report/{token}.md")
async def export_markdown(token: str):
    cached = _cache_get(token)
    if not cached:
        return PlainTextResponse("This report has expired. Run the analysis again.", 404)
    report, _resume = cached
    return PlainTextResponse(
        to_markdown(report),
        headers={"Content-Disposition": 'attachment; filename="resume-diagnostics.md"'},
    )


@app.get("/report/{token}.pdf")
async def export_pdf(token: str):
    cached = _cache_get(token)
    if not cached:
        return PlainTextResponse("This report has expired. Run the analysis again.", 404)
    report, _resume = cached
    return Response(
        to_pdf(report),
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="resume-diagnostics.pdf"'},
    )


@app.get("/healthz", response_class=PlainTextResponse)
async def healthz():
    return "ok"
