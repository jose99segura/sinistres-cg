"""HTTP API and the static web page."""

import json
import threading
from typing import Literal
import time
from collections import defaultdict, deque
from functools import lru_cache

import pymupdf
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import config, db, llm
from .answer.analyse import analyse
from .taxonomy import KIND_LABELS, PERIL_LABELS, PERIL_LABELS_EN

WEB = config.ROOT / "sinistres" / "web"
EVAL_REPORT = config.ROOT / "eval" / "report.json"

app = FastAPI(title="Sinistres et conditions générales", docs_url="/api/docs")
app.mount("/static", StaticFiles(directory=WEB), name="static")

_conn = None


def conn():
    global _conn
    if _conn is None:
        _conn = db.connect(readonly=True)
    return _conn


# ---------------------------------------------------------------- rate limit (public demo)

_lock = threading.Lock()
_per_ip: dict[str, deque] = defaultdict(deque)
_day = {"date": "", "count": 0}


def _check_rate(ip: str) -> None:
    now = time.time()
    today = time.strftime("%Y-%m-%d")
    with _lock:
        if _day["date"] != today:
            _day.update(date=today, count=0)
        if _day["count"] >= config.RATE_GLOBAL_DAY:
            raise HTTPException(429, "Limite quotidienne de la démo atteinte. Réessayez demain.")
        q = _per_ip[ip]
        while q and now - q[0] > 3600:
            q.popleft()
        if len(q) >= config.RATE_PER_IP_HOUR:
            raise HTTPException(429, "Trop d'analyses depuis votre adresse. Réessayez dans une heure.")
        q.append(now)
        _day["count"] += 1


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    return forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "?")


# ---------------------------------------------------------------- routes


@app.get("/")
def index():
    # Always revalidate the page: it names the versioned static files, so a stale copy would load old code.
    return FileResponse(WEB / "index.html", headers={"Cache-Control": "no-cache"})


@app.get("/health")
def health():
    n = conn().execute("select count(*) from clauses").fetchone()[0]
    return {"ok": True, "clauses": n}


@app.get("/api/contracts")
def contracts():
    return {
        "contracts": db.contracts(conn()),
        "kinds": KIND_LABELS,
        "perils": {"fr": PERIL_LABELS, "en": PERIL_LABELS_EN},
    }


class AnalyseIn(BaseModel):
    contract_id: str
    claim: str = Field(min_length=15, max_length=1500)
    lang: Literal["fr", "en"] = "fr"


@app.post("/api/analyse")
def post_analyse(body: AnalyseIn, request: Request):
    if not conn().execute("select 1 from contracts where id = ?", (body.contract_id,)).fetchone():
        raise HTTPException(404, "Contrat inconnu.")
    _check_rate(_client_ip(request))
    try:
        return analyse(body.contract_id, body.claim.strip(), lang=body.lang)
    except llm.LLMError:
        raise HTTPException(503, "Le modèle ne répond pas pour le moment (limite du niveau gratuit). Réessayez dans une minute.")


@app.get("/api/clauses/{clause_id}")
def clause(clause_id: str):
    rows = db.clauses_by_ids(conn(), [clause_id])
    if not rows:
        raise HTTPException(404)
    return rows[0]


@lru_cache(maxsize=8)
def _pdf(contract_id: str) -> pymupdf.Document:
    return pymupdf.open(config.PDF_DIR / f"{contract_id}.pdf")


_render_lock = threading.Lock()


@app.get("/api/page/{contract_id}/{page}.png")
def page_png(contract_id: str, page: int, lines: str = ""):
    """The PDF page as an image, with the cited lines highlighted."""
    if not conn().execute("select 1 from contracts where id = ?", (contract_id,)).fetchone():
        raise HTTPException(404)
    wanted = [int(x) for x in lines.split(",") if x.isdigit()][:200]
    rects = []
    if wanted:
        marks = ",".join("?" * len(wanted))
        rects = conn().execute(
            f"select x0, y0, x1, y1 from lines where contract_id = ? and page = ? and n in ({marks})",
            (contract_id, page, *wanted),
        ).fetchall()
    with _render_lock:  # a PyMuPDF document is not thread-safe
        doc = _pdf(contract_id)
        if not 1 <= page <= doc.page_count:
            raise HTTPException(404)
        if not rects:
            pix = doc[page - 1].get_pixmap(dpi=110)
        else:
            # Draw on a one-page copy so the cached document stays clean.
            tmp = pymupdf.open()
            tmp.insert_pdf(doc, from_page=page - 1, to_page=page - 1)
            shape = tmp[0].new_shape()
            for x0, y0, x1, y1 in rects:
                shape.draw_rect(pymupdf.Rect(x0 - 2, y0 - 1, x1 + 2, y1 + 1))
            shape.finish(color=None, fill=(1, 0.86, 0.2), fill_opacity=0.38)
            shape.commit(overlay=True)
            pix = tmp[0].get_pixmap(dpi=110)
            tmp.close()
        png = pix.tobytes("png")
    return Response(png, media_type="image/png", headers={"Cache-Control": "public, max-age=86400"})


@app.get("/api/eval")
def eval_report():
    if not EVAL_REPORT.exists():
        return JSONResponse({"available": False})
    return json.loads(EVAL_REPORT.read_text(encoding="utf-8"))
