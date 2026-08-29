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
from ats.pipeline import ExtractionError, RunInput, analyze
from ats.report import to_markdown, to_pdf

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("ats.app")

ROOT = Path(__file__).parent
MAX_UPLOAD_BYTES = 12 * 1024 * 1024
CACHE_TTL_SECONDS = 3600
CACHE_LIMIT = 24

app = FastAPI(title="resume.diagnostics", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
templates = Jinja2Templates(directory=str(ROOT / "templates"))

# token -> (created_at, Report). Keeps export cheap and stops a re-render from
# re-running (or re-billing) the analysis.
_CACHE: dict[str, tuple[float, Report]] = {}


def _cache_put(report: Report, seed: str) -> str:
    _prune()
    token = hashlib.sha256(f"{seed}{time.time()}".encode()).hexdigest()[:16]
    _CACHE[token] = (time.time(), report)
    return token


def _cache_get(token: str) -> Report | None:
    _prune()
    entry = _CACHE.get(token)
    return entry[1] if entry else None


def _prune() -> None:
    now = time.time()
    for key in [k for k, (t, _) in _CACHE.items() if now - t > CACHE_TTL_SECONDS]:
        _CACHE.pop(key, None)
    while len(_CACHE) > CACHE_LIMIT:
        _CACHE.pop(min(_CACHE, key=lambda k: _CACHE[k][0]), None)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html", {})


@app.post("/analyze", response_class=HTMLResponse)
async def do_analyze(
    request: Request,
    pdf: UploadFile,
    jd: str = Form(""),
    anthropic_key: str = Form(""),
    openai_key: str = Form(""),
    mode: str = Form("default"),
    rewrites: str = Form(""),
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
            ensemble_mode=mode if mode in {"economy", "default", "thorough"} else "default",
            enable_rewrites=bool(rewrites),
        )
        started = time.time()
        report = analyze(run)
        report.run_meta["elapsed_seconds"] = round(time.time() - started, 1)
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

    token = _cache_put(report, hashlib.sha256(payload).hexdigest())
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
    report = _cache_get(token)
    if not report:
        return PlainTextResponse("This report has expired. Run the analysis again.", 404)
    return PlainTextResponse(
        to_markdown(report),
        headers={"Content-Disposition": 'attachment; filename="resume-diagnostics.md"'},
    )


@app.get("/report/{token}.pdf")
async def export_pdf(token: str):
    report = _cache_get(token)
    if not report:
        return PlainTextResponse("This report has expired. Run the analysis again.", 404)
    return Response(
        to_pdf(report),
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="resume-diagnostics.pdf"'},
    )


@app.get("/healthz", response_class=PlainTextResponse)
async def healthz():
    return "ok"
