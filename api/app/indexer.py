"""Keeps the evidence collection in step with PostgreSQL.

Three kinds of points share one collection:
  - report: synthetic inspection reports, ingested through RAGWire sync
  - record: one point per current CSV row, with a stable id and a fingerprint
  - vessel_summary: one point per vessel, from the latest risk snapshot

Record and summary points carry no metadata.source, because RAGWire's sync
treats every stored source it does not list as deleted.
"""

import hashlib
import json
import logging
import threading
import uuid
from datetime import date

import pandas as pd
from langchain_core.documents import Document
from qdrant_client import models
from sqlalchemy import select, update
from sqlalchemy.engine import Engine

from . import service
from .db import actions, uploads
from .rag import EvidenceStore, ai_status, get_store, relax_timeout
from .reports import build_reports, date_num, iso, write_reports
from .schemas import TABLE_SPECS
from .upload import current_data_version

logger = logging.getLogger(__name__)

POINT_NAMESPACE = uuid.UUID("5d0f6a52-8f55-4d2b-9c43-6a2c1f0e7b11")
EMBED_BATCH = 16
REPORT_TABLES = {"vessels", "inspections", "deficiencies", "detentions"}


def point_id(evidence_id: str) -> str:
    return str(uuid.uuid5(POINT_NAMESPACE, evidence_id))


def fingerprint(text: str, metadata: dict) -> str:
    stable = {k: v for k, v in metadata.items() if k not in ("upload_id", "fingerprint")}
    blob = text + "\n" + json.dumps(stable, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _low(value) -> str | None:
    return None if value is None or pd.isna(value) else str(value).strip().lower()


def _row_text_and_meta(table: str, r, vname: str, ins_dates: dict) -> tuple[str, dict]:
    who = f"{vname} ({r.vessel_id})"
    if table == "vessels":
        return (f"{who} is a {r.vessel_type} built in {r.build_year}, flag {r.flag_state}, IMO {r.imo_number}.",
                {"category": _low(r.vessel_type)})
    if table == "inspections":
        return (f"{who} had a {r.inspection_type} inspection {r.inspection_id} by {r.inspection_authority} "
                f"at {r.inspection_port} on {iso(r.inspection_date)}. Result: {r.inspection_result}.",
                {"date": iso(r.inspection_date), "date_num": date_num(r.inspection_date),
                 "status": _low(r.inspection_result), "category": _low(r.inspection_type),
                 "inspection_id": r.inspection_id})
    if table == "deficiencies":
        raised = ins_dates.get(r.inspection_id)
        status = (f"Closed on {iso(r.deficiency_closed_date)}" if r.deficiency_status == "Closed" else "Open")
        return (f"Deficiency {r.deficiency_id} ({r.deficiency_code}, {r.deficiency_category}) on {who}, "
                f"raised at inspection {r.inspection_id} on {iso(raised)}: {r.deficiency_description}. "
                f"Status: {status}.",
                {"date": iso(raised), "date_num": date_num(raised), "status": _low(r.deficiency_status),
                 "category": _low(r.deficiency_category), "inspection_id": r.inspection_id,
                 "deficiency_code": r.deficiency_code})
    if table == "detentions":
        return (f"{who} was detained on {iso(r.detention_date)} after inspection {r.inspection_id}. "
                f"Reason: {r.detention_reason}.",
                {"date": iso(r.detention_date), "date_num": date_num(r.detention_date), "status": "detained",
                 "inspection_id": r.inspection_id})
    if table == "audit_findings":
        return (f"Audit finding {r.audit_id} on {who}: {r.audit_finding_description}. "
                f"Status: {r.audit_finding_status}.",
                {"status": _low(r.audit_finding_status)})
    if table == "crew":
        return (f"Crew member {r.crew_id} on {who}: {r.rank}, joined on {iso(r.join_date)}, "
                f"{r.rank_experience_months} months experience in rank. Training: {r.training_status}. "
                f"STCW certificate: {r.stcw_status}.",
                {"date": iso(r.join_date), "date_num": date_num(r.join_date), "status": _low(r.training_status),
                 "category": _low(r.rank), "stcw_status": _low(r.stcw_status)})
    if table == "equipment_failures":
        return (f"Equipment failure {r.failure_id} on {who}: {r.equipment_name} failed on "
                f"{iso(r.equipment_failure_date)}. {r.equipment_failure_description}.",
                {"date": iso(r.equipment_failure_date), "date_num": date_num(r.equipment_failure_date),
                 "category": _low(r.equipment_name)})
    if table == "maintenance":
        done = f", completed on {iso(r.maintenance_completed_date)}" if r.maintenance_status == "Completed" else ""
        return (f"Maintenance job {r.maintenance_id} on {who}: {r.maintenance_equipment_name}, due on "
                f"{iso(r.maintenance_due_date)}. Status: {r.maintenance_status}{done}.",
                {"date": iso(r.maintenance_due_date), "date_num": date_num(r.maintenance_due_date),
                 "status": _low(r.maintenance_status), "category": _low(r.maintenance_equipment_name)})
    raise ValueError(f"No record template for table {table}")


def row_documents(frames: dict[str, pd.DataFrame], version: dict) -> list[Document]:
    names = dict(zip(frames["vessels"]["vessel_id"], frames["vessels"]["vessel_name"]))
    ins_dates = dict(zip(frames["inspections"]["inspection_id"], frames["inspections"]["inspection_date"]))
    docs = []
    for table, spec in TABLE_SPECS.items():
        for r in frames[table].itertuples(index=False):
            key = getattr(r, spec.key)
            text, extra = _row_text_and_meta(table, r, names.get(r.vessel_id, r.vessel_id), ins_dates)
            meta = {
                "source_type": "record", "table": table, "vessel_id": r.vessel_id,
                "vessel_name": names.get(r.vessel_id), "record_id": key,
                "evidence_id": f"{table}:{key}", "label": f"{spec.file_stem}.csv {key}",
                **{k: v for k, v in extra.items() if v is not None},
                "upload_id": version.get(table),
            }
            meta["fingerprint"] = fingerprint(text, meta)
            docs.append(Document(page_content=text, metadata=meta))
    return docs


def _list(items: list[str], empty: str) -> str:
    return "; ".join(items) if items else empty


def summary_documents(snapshots: list[dict], open_actions: list[dict], names: dict[str, str]) -> list[Document]:
    by_vessel: dict[str, list[dict]] = {}
    for a in open_actions:
        by_vessel.setdefault(a["vessel_id"], []).append(a)
    docs = []
    for s in snapshots:
        vid = s["vessel_id"]
        name = names.get(vid, vid)
        as_of = s["as_of"] if isinstance(s["as_of"], date) else date.fromisoformat(str(s["as_of"]))
        drivers = [f"{d['text']} ({d['points']:.1f} points, records {', '.join(d['record_ids'][:6])})"
                   for d in s["drivers"]]
        overrides = [o["text"] for o in s["overrides"]]
        acts = [f"{a['text']} (owner {a['owner']}, due {a['due_date']})" for a in by_vessel.get(vid, [])]
        text = (f"Current risk summary for {name} ({vid}) as of {as_of.isoformat()}: "
                f"score {s['score']:.0f} out of 100, band {s['band']}, confidence {s['confidence']}.\n"
                f"Main drivers: {_list(drivers, 'none')}.\n"
                f"Overrides: {_list(overrides, 'none')}.\n"
                f"Open actions: {_list(acts, 'none')}.")
        meta = {
            "source_type": "vessel_summary", "doc_type": "summary", "vessel_id": vid, "vessel_name": name,
            "evidence_id": f"summary:{vid}", "label": f"Risk summary {vid}", "status": s["band"].lower(),
            "date": as_of.isoformat(), "date_num": date_num(as_of), "calc_id": s["calc_id"],
        }
        meta["fingerprint"] = fingerprint(text, meta)
        docs.append(Document(page_content=text, metadata=meta))
    return docs


def _match(key: str, value) -> models.FieldCondition:
    return models.FieldCondition(key=f"metadata.{key}", match=models.MatchValue(value=value))


def _existing(store: EvidenceStore, source_type: str) -> dict[str, str | None]:
    found, offset = {}, None
    while True:
        points, offset = store.client.scroll(
            store.collection, scroll_filter=models.Filter(must=[_match("source_type", source_type)]),
            limit=512, offset=offset, with_payload=["metadata.fingerprint"])
        for p in points:
            found[str(p.id)] = (p.payload or {}).get("metadata", {}).get("fingerprint")
        if offset is None:
            return found


def sync_points(store: EvidenceStore, docs: list[Document], source_type: str) -> dict:
    """Embed new or changed points, delete points no longer present."""
    relax_timeout(store.client)
    existing = _existing(store, source_type)
    wanted = {point_id(d.metadata["evidence_id"]): d for d in docs}
    changed = [(pid, d) for pid, d in wanted.items() if existing.get(pid) != d.metadata["fingerprint"]]
    for i in range(0, len(changed), EMBED_BATCH):
        batch = changed[i:i + EMBED_BATCH]
        store.vectorstore.add_documents([d for _, d in batch], ids=[pid for pid, _ in batch])
    stale = [pid for pid in existing if pid not in wanted]
    if stale:
        store.client.delete(store.collection, points_selector=models.PointIdsList(points=stale))
    return {"total": len(wanted), "embedded": len(changed), "deleted": len(stale)}


def mark_current(store: EvidenceStore, version: dict) -> None:
    """Record unchanged rows as belonging to the current upload of their table."""
    for table, upload_id in version.items():
        if upload_id is None:
            continue
        store.client.set_payload(
            store.collection, payload={"upload_id": upload_id}, key="metadata",
            points=models.Filter(must=[_match("source_type", "record"), _match("table", table)]))


def sync_reports(store: EvidenceStore, frames: dict[str, pd.DataFrame]) -> dict:
    from ragwire.sources.local import LocalSource

    rag = store.rag
    files = write_reports(rag.reports_dir, build_reports(frames))
    synced = rag.sync(sources=[LocalSource(path=str(rag.reports_dir), extensions=[".md"])])
    if synced["errors"] or synced["failed"]:
        raise RuntimeError(f"Report sync failed: {synced['errors'][:3]}")
    return {"files": files, "sync": {k: synced[k] for k in ("listed", "processed", "skipped", "replaced", "deleted")}}


def reindex(engine: Engine, store: EvidenceStore, include_reports: bool = True) -> dict:
    with engine.connect() as conn:
        frames = service.load_current_frames(conn)
        version = current_data_version(conn)
        snapshots = service.snapshots_for(conn, service.latest_calc_id(conn))
        open_actions = [dict(a) for a in conn.execute(
            select(actions).where(actions.c.status == "open").order_by(actions.c.id)).mappings()]
    if version.get("vessels") is None:
        return {"skipped": "no data loaded"}

    stats: dict = {"data_version": version}
    if include_reports and store.rag is not None:
        stats["reports"] = sync_reports(store, frames)
    stats["records"] = sync_points(store, row_documents(frames, version), "record")
    mark_current(store, version)
    names = dict(zip(frames["vessels"]["vessel_id"], frames["vessels"]["vessel_name"]))
    stats["summaries"] = sync_points(store, summary_documents(snapshots, open_actions, names), "vessel_summary")
    return stats


_run_lock = threading.Lock()


def run_indexing(engine: Engine, include_reports: bool = True, actor: str = "system") -> dict:
    """Re-index and mark uploads up to the indexed data version as indexed.

    Uploads that commit while a run is in progress stay index_pending for the next run.
    """
    status = ai_status()
    if not status["enabled"]:
        return {"skipped": f"AI features are disabled: {status['reason']}"}
    with _run_lock:
        try:
            stats = reindex(engine, get_store(), include_reports)
        except Exception as exc:
            logger.exception("Indexing failed")
            with engine.begin() as conn:
                service.log_event(conn, "index_failed", actor, {"error": str(exc)[:500]})
            raise
        indexed_up_to = max((u for u in stats.get("data_version", {}).values() if u is not None), default=None)
        with engine.begin() as conn:
            if indexed_up_to is not None:
                conn.execute(update(uploads).where(uploads.c.status == "index_pending", uploads.c.id <= indexed_up_to)
                             .values(status="indexed"))
            service.log_event(conn, "index", actor, {k: v for k, v in stats.items() if k != "data_version"})
    return stats


def run_indexing_quietly(engine: Engine, include_reports: bool = True, actor: str = "system") -> None:
    """Background-task wrapper: failures are logged and audited, uploads stay pending for a retry."""
    try:
        run_indexing(engine, include_reports, actor)
    except Exception:
        pass


def point_counts(store: EvidenceStore) -> dict[str, int]:
    return {
        kind: store.client.count(store.collection, count_filter=models.Filter(must=[_match("source_type", kind)]),
                                 exact=True).count
        for kind in ("report", "record", "vessel_summary")
    }
