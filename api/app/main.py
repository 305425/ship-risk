import os
import secrets
import urllib.request
from contextlib import asynccontextmanager
from datetime import date
from functools import lru_cache
from typing import Annotated, Literal

import pandas as pd
from fastapi import BackgroundTasks, Depends, FastAPI, File, Header, HTTPException, Query, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field
from sqlalchemy import func, select, text

from . import assistant, evidence, indexer, records, service
from .backtest import run_backtest
from .model_registry import retrain_quietly, serve
from .risk_model import ShadowModelError
from .chat_history import ensure_chat_tables
from .config import get_settings
from .db import actions, get_engine, risk_snapshots, uploads
from .rag import ai_status, get_store
from .schemas import TABLE_SPECS
from .scoring import load_rules
from .tracing import configure_tracing
from .upload import UploadRejected, current_data_version, save_upload, upload_diff, validate_upload

MAX_UPLOAD_BYTES = 10 * 1024 * 1024


@asynccontextmanager
async def lifespan(_app):
    # Cache the SQLAlchemy URL, create the chat tables, then drop DATABASE_URL.
    # Chainlit's automatic path imports asyncpg whenever that variable is set.
    # The chat data layer opens this same database itself.
    get_settings()
    configure_tracing()
    ensure_chat_tables()
    os.environ.pop("DATABASE_URL", None)
    yield


app = FastAPI(
    title="Ship Detention Early Warning System",
    version="0.1.0",
    lifespan=lifespan,
    description="Fleet detention-risk scores, evidence search, and the shadow model. Protected routes expect the dashboard API key.",
    docs_url=None,
    redoc_url="/redoc",
)

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False, scheme_name="API key")


@app.get("/docs", include_in_schema=False)
def swagger_ui() -> HTMLResponse:
    """Swagger UI. The preset script is loaded separately; the bundle no longer includes it."""
    return HTMLResponse(
        """<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css">
<title>Ship Detention Early Warning System - Swagger UI</title>
</head>
<body>
<div id="swagger-ui"></div>
<script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
<script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-standalone-preset.js"></script>
<script>
SwaggerUIBundle({
  url: "/openapi.json",
  dom_id: "#swagger-ui",
  deepLinking: true,
  persistAuthorization: true,
  presets: [SwaggerUIBundle.presets.apis, SwaggerUIStandalonePreset],
  layout: "StandaloneLayout",
})
</script>
</body>
</html>"""
    )


@lru_cache
def get_rules() -> dict:
    return load_rules(get_settings().rules_path)


def require_api_key(x_api_key: Annotated[str | None, Depends(api_key_header)]) -> None:
    expected = get_settings().api_key
    if not expected:
        raise HTTPException(503, "API_KEY is not configured on the server")
    if x_api_key is None or not secrets.compare_digest(x_api_key, expected):
        raise HTTPException(401, "Missing or invalid X-API-Key header")


def actor(x_user: Annotated[str | None, Header()] = None) -> str:
    return (x_user or "api-user").strip()[:100] or "api-user"


Auth = Depends(require_api_key)
Actor = Annotated[str, Depends(actor)]


@app.get("/api/health")
def health() -> dict:
    status = {"postgres": "down", "qdrant": "down"}
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        status["postgres"] = "up"
    except Exception:
        pass
    try:
        with urllib.request.urlopen(f"{get_settings().qdrant_url}/readyz", timeout=2) as resp:
            if resp.status == 200:
                status["qdrant"] = "up"
    except Exception:
        pass
    status["status"] = "ok" if all(v == "up" for v in status.values()) else "degraded"
    return status


# --- Upload ----------------------------------------------------------------------------------------------------

@app.post("/api/upload", dependencies=[Auth])
async def upload_csvs(files: Annotated[list[UploadFile], File()], user: Actor, background: BackgroundTasks):
    contents = []
    for f in files:
        data = await f.read(MAX_UPLOAD_BYTES + 1)
        if len(data) > MAX_UPLOAD_BYTES:
            raise HTTPException(413, f"{f.filename} is larger than {MAX_UPLOAD_BYTES // (1024 * 1024)} MB")
        contents.append((f.filename or "unnamed.csv", data))

    rules, as_of = get_rules(), get_settings().today()
    try:
        with get_engine().begin() as conn:
            service.lock_recalculation(conn)
            batch = validate_upload(conn, contents)
            before = service.snapshots_for(conn, service.latest_calc_id(conn))
            saved = save_upload(conn, batch, user)
            calc = service.recalculate(conn, rules, as_of, "upload", saved["batch_id"], user)
            after = service.snapshots_for(conn, calc["calc_id"])
            service.log_event(conn, "upload", user, {"batch_id": saved["batch_id"], "files": saved["files"]})
    except UploadRejected as exc:
        return JSONResponse(status_code=422, content={"detail": "Validation failed, nothing was saved",
                                                      "errors": [e.as_dict() for e in exc.errors]})
    include_reports = any(f["table"] in indexer.REPORT_TABLES for f in saved["files"])
    background.add_task(indexer.run_indexing_quietly, get_engine(), include_reports, user)
    background.add_task(retrain_quietly, get_engine(), rules, as_of, saved["batch_id"])
    return {**saved, "actions": calc["actions"], "ranking_changes": service.ranking_changes(before, after),
            "indexing": "scheduled" if ai_status()["enabled"] else "disabled", "model": "scheduled"}


@app.get("/api/uploads", dependencies=[Auth])
def list_uploads():
    with get_engine().connect() as conn:
        return [dict(r) for r in conn.execute(select(uploads).order_by(uploads.c.id.desc())).mappings()]


@app.get("/api/uploads/{upload_id}/diff", dependencies=[Auth])
def get_upload_diff(upload_id: int):
    with get_engine().connect() as conn:
        diff = upload_diff(conn, upload_id)
        if diff is None:
            raise HTTPException(404, "Upload not found")
        first = conn.execute(
            select(risk_snapshots.c.id, risk_snapshots.c.calc_id)
            .where(risk_snapshots.c.trigger == "upload", risk_snapshots.c.trigger_ref == diff["upload"]["batch_id"])
            .order_by(risk_snapshots.c.id).limit(1)
        ).first()
        before = service.snapshots_for(conn, service.latest_calc_id(conn, first.id)) if first else []
        after = service.snapshots_for(conn, first.calc_id) if first else []
    return {**diff, "ranking_changes": service.ranking_changes(before, after)}


# --- Risk ------------------------------------------------------------------------------------------------------

def _latest(conn) -> list[dict]:
    snaps = service.snapshots_for(conn, service.latest_calc_id(conn))
    if not snaps:
        raise HTTPException(404, "No risk scores yet: upload the CSV data first")
    return snaps


def _vessel_snapshot(conn, vessel_id: str) -> dict:
    snap = next((s for s in _latest(conn) if s["vessel_id"] == vessel_id), None)
    if snap is None:
        raise HTTPException(404, f"Unknown vessel {vessel_id}")
    return snap


def _vessel_names(conn) -> dict[str, str]:
    return {r.vessel_id: r.vessel_name for r in conn.execute(text("SELECT vessel_id, vessel_name FROM current_vessels"))}


@app.get("/api/fleet/ranking", dependencies=[Auth])
def fleet_ranking():
    with get_engine().connect() as conn:
        snaps, names = _latest(conn), _vessel_names(conn)
    return [
        {"rank": i + 1, "vessel_id": s["vessel_id"], "vessel_name": names.get(s["vessel_id"]), "score": s["score"],
         "band": s["band"], "confidence": s["confidence"], "overrides": [o["text"] for o in s["overrides"]],
         "drivers": s["drivers"], "as_of": s["as_of"], "calc_id": s["calc_id"]}
        for i, s in enumerate(snaps)
    ]


@app.get("/api/vessels/{vessel_id}/risk", dependencies=[Auth])
def vessel_risk(vessel_id: str):
    with get_engine().connect() as conn:
        snap = _vessel_snapshot(conn, vessel_id)
        snap["vessel_name"] = _vessel_names(conn).get(vessel_id)
    return snap


@app.get("/api/vessels/{vessel_id}/history", dependencies=[Auth])
def vessel_history(vessel_id: str):
    with get_engine().connect() as conn:
        rows = conn.execute(
            select(risk_snapshots.c.created_at, risk_snapshots.c.trigger, risk_snapshots.c.trigger_ref,
                   risk_snapshots.c.score, risk_snapshots.c.band, risk_snapshots.c.calc_id)
            .where(risk_snapshots.c.vessel_id == vessel_id).order_by(risk_snapshots.c.id)
        ).mappings()
        return [dict(r) for r in rows]


@app.get("/api/vessels/{vessel_id}/issues", dependencies=[Auth])
def vessel_issues(vessel_id: str):
    with get_engine().connect() as conn:
        _vessel_snapshot(conn, vessel_id)
        frames = {t: f[f.vessel_id == vessel_id] for t, f in service.load_current_frames(conn).items()}
    as_of = pd.Timestamp(get_settings().today())

    def records(frame: pd.DataFrame) -> list[dict]:
        return frame.astype(object).where(frame.notna(), None).to_dict("records")

    defs = frames["deficiencies"].merge(frames["inspections"][["inspection_id", "inspection_date"]], on="inspection_id")
    maint = frames["maintenance"]
    due = pd.to_datetime(maint.maintenance_due_date)
    crew = frames["crew"]
    return {
        "open_deficiencies": records(defs[defs.deficiency_status == "Open"].sort_values("inspection_date")),
        "unresolved_audit_findings": records(frames["audit_findings"][frames["audit_findings"].audit_finding_status != "Closed"]),
        "overdue_maintenance": records(maint[maint.maintenance_status == "Overdue"].sort_values("maintenance_due_date")),
        "stale_open_maintenance": records(maint[(maint.maintenance_status == "Open") & (due < as_of)]),
        "crew_flags": records(crew[(crew.training_status != "Compliant") | (crew.stcw_status != "Valid")]),
    }


@app.get("/api/records/{record_id}", dependencies=[Auth])
def record_detail(record_id: str):
    """One current row: a bare id such as INS0001 or an evidence id such as maintenance:MAIN0001."""
    with get_engine().connect() as conn:
        found = records.find_record(conn, record_id)
    if found is None:
        raise HTTPException(404, f"No record {record_id}")
    return found


@app.get("/api/backtest", dependencies=[Auth])
def backtest(top_n: int = 2):
    if not 1 <= top_n <= 20:
        raise HTTPException(422, "top_n must be between 1 and 20")
    with get_engine().connect() as conn:
        frames = service.load_current_frames(conn)
    if frames["vessels"].empty:
        raise HTTPException(404, "No data yet: upload the CSV data first")
    return run_backtest(frames, get_rules(), top_n)


@app.get("/api/risk-model", dependencies=[Auth])
def risk_model():
    """Shadow logistic regression. Does not change the stored rule score or band."""
    with get_engine().connect() as conn:
        frames = service.load_current_frames(conn)
    if frames["vessels"].empty:
        raise HTTPException(404, "No data yet: upload the CSV data first")
    try:
        return serve(frames, get_rules(), get_settings().today())
    except ShadowModelError as exc:
        raise HTTPException(422, str(exc)) from exc


# --- Actions ---------------------------------------------------------------------------------------------------

class CompleteAction(BaseModel):
    evidence: str = Field(min_length=3, max_length=2000)


@app.get("/api/vessels/{vessel_id}/actions", dependencies=[Auth])
def vessel_actions(vessel_id: str, include_closed: bool = False):
    query = select(actions).where(actions.c.vessel_id == vessel_id)
    if not include_closed:
        query = query.where(actions.c.status == "open")
    with get_engine().connect() as conn:
        return [dict(r) for r in conn.execute(query.order_by(actions.c.due_date, actions.c.id)).mappings()]


@app.post("/api/vessels/{vessel_id}/actions/{action_id}/complete", dependencies=[Auth])
def complete_vessel_action(vessel_id: str, action_id: int, body: CompleteAction, user: Actor,
                           background: BackgroundTasks):
    try:
        with get_engine().begin() as conn:
            result = service.complete_action(conn, action_id, vessel_id, body.evidence, user,
                                             get_rules(), get_settings().today())
    except ValueError as exc:
        raise HTTPException(409, str(exc))
    if result is None:
        raise HTTPException(404, "Action not found for this vessel")
    background.add_task(indexer.run_indexing_quietly, get_engine(), False, user)
    return result


# --- Evidence --------------------------------------------------------------------------------------------------

def _require_store():
    try:
        store = get_store()
    except Exception as exc:
        raise HTTPException(503, f"Evidence store is unavailable: {exc}") from exc
    if store is None:
        status = ai_status()
        raise HTTPException(503, f"Evidence search is unavailable: {status['reason']}. "
                                 "Use /api/vessels/{id}/issues for the underlying records.")
    return store


@app.get("/api/vessels/{vessel_id}/evidence", dependencies=[Auth])
def vessel_evidence(
    vessel_id: str,
    user: Actor,
    q: Annotated[str, Query(min_length=3, max_length=500)],
    source_type: Literal["record", "report", "vessel_summary"] | None = None,
    table: Literal[tuple(TABLE_SPECS)] | None = None,
    doc_type: Literal["inspection_report", "summary"] | None = None,
    status: Annotated[str | None, Query(max_length=40)] = None,
    category: Annotated[str | None, Query(max_length=80)] = None,
    date_from: Annotated[date | None, Query(alias="from")] = None,
    date_to: Annotated[date | None, Query(alias="to")] = None,
    k: Annotated[int, Query(ge=1, le=10)] = 5,
):
    with get_engine().connect() as conn:
        _vessel_snapshot(conn, vessel_id)
        version = current_data_version(conn)
    store = _require_store()
    filters = evidence.EvidenceFilters(source_type, table, doc_type, status, category, date_from, date_to)
    docs = evidence.search(store, q, evidence.build_filter(vessel_id, version, filters), k)
    result = evidence.answer(store, q, docs)
    with get_engine().begin() as conn:
        service.log_event(conn, "llm_call", user, {
            "endpoint": "evidence", "vessel_id": vessel_id, "query": q, "filters": filters.as_dict(),
            "model": store.model, "prompt_version": store.prompt_version, "retrieved": len(docs),
            "refused": result["refused"], "citations": [c["evidence_id"] for c in result["citations"]],
        })
    return {"vessel_id": vessel_id, "query": q, "filters": filters.as_dict(), "model": store.model,
            "retrieved": len(docs), **result}


@app.get("/api/index/status", dependencies=[Auth])
def index_status():
    with get_engine().connect() as conn:
        pending = conn.execute(select(func.count()).select_from(uploads)
                               .where(uploads.c.status == "index_pending")).scalar_one()
        last = conn.execute(text("SELECT event_type, created_at, details FROM audit_log "
                                 "WHERE event_type IN ('index', 'index_failed') ORDER BY id DESC LIMIT 1")).mappings().first()
    status = {**ai_status(), "uploads_pending": pending, "last_run": dict(last) if last else None}
    if status["enabled"]:
        try:
            store = get_store()
            status["collection"] = store.collection
            status["points"] = indexer.point_counts(store)
        except Exception as exc:
            status["store_error"] = str(exc)[:300]
    return status


@app.post("/api/index/retry", dependencies=[Auth])
def index_retry(user: Actor):
    _require_store()
    try:
        return indexer.run_indexing(get_engine(), True, user)
    except Exception as exc:
        raise HTTPException(502, f"Indexing failed: {str(exc)[:300]}") from exc


# --- Assistant -------------------------------------------------------------------------------------------------

class AskBody(BaseModel):
    question: str = Field(min_length=3, max_length=500)


@app.post("/api/vessels/{vessel_id}/ask", dependencies=[Auth])
def vessel_ask(vessel_id: str, body: AskBody, user: Actor):
    with get_engine().connect() as conn:
        _vessel_snapshot(conn, vessel_id)
    return assistant.run(vessel_id, body.question, user)


os.environ.setdefault("CHAINLIT_AUTH_SECRET", secrets.token_hex(32))
from chainlit.utils import mount_chainlit

mount_chainlit(app, target="app/cl_app.py", path="/chat")
