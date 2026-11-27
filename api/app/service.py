"""Recalculation, score snapshots, action sync and readiness. All functions run inside the caller's transaction."""

import uuid
from datetime import date

import pandas as pd
from sqlalchemy import func, insert, select, text, update
from sqlalchemy.engine import Connection

from . import actions as action_engine
from .db import actions, audit_log, risk_snapshots
from .schemas import LOAD_ORDER
from .scoring import score_fleet
from .upload import current_data_version

RECALC_LOCK_ID = 4242


def lock_recalculation(conn: Connection) -> None:
    conn.execute(text("SELECT pg_advisory_xact_lock(:id)"), {"id": RECALC_LOCK_ID})


def log_event(conn: Connection, event_type: str, actor: str, details: dict) -> None:
    conn.execute(insert(audit_log), {"event_type": event_type, "actor": actor, "details": details})


def load_current_frames(conn: Connection) -> dict[str, pd.DataFrame]:
    frames = {}
    for table in LOAD_ORDER:
        frame = pd.read_sql(text(f"SELECT * FROM current_{table}"), conn)
        frames[table] = frame.drop(columns=["upload_id"])
    return frames


def _rules_by_id(rules: dict) -> dict[str, dict]:
    return {r["id"]: r for r in rules["actions"]}


def _still_effective(action: dict, rule: dict | None, version: dict) -> bool:
    if rule is None or not action["completed_data_version"]:
        return False
    table = action_engine.watched_table(rule)
    return action["completed_data_version"].get(table) == version.get(table)


def resolved_records(conn: Connection, rules: dict, version: dict) -> dict[str, set[str]]:
    by_id = _rules_by_id(rules)
    resolved: dict[str, set[str]] = {}
    for a in conn.execute(select(actions).where(actions.c.status == "completed")).mappings():
        if _still_effective(a, by_id.get(a["rule_id"]), version):
            for table, ids in a["resolves"].items():
                resolved.setdefault(table, set()).update(ids)
    return resolved


def _sync_actions(conn: Connection, results: list[dict], rules: dict, version: dict, as_of: date) -> dict:
    by_id = _rules_by_id(rules)
    existing = [dict(a) for a in conn.execute(select(actions).where(actions.c.status.in_(["open", "completed"]))).mappings()]
    open_by_key = {a["action_key"]: a for a in existing if a["status"] == "open"}
    done_keys = {a["action_key"] for a in existing
                 if a["status"] == "completed" and _still_effective(a, by_id.get(a["rule_id"]), version)}

    planned = [p for r in results for p in action_engine.plan_actions(r, rules, as_of)]
    created = updated = 0
    for p in planned:
        current = open_by_key.pop(p["action_key"], None)
        if current is not None:
            if current["record_ids"] != p["record_ids"] or current["text"] != p["text"]:
                conn.execute(update(actions).where(actions.c.id == current["id"]).values(
                    text=p["text"], record_ids=p["record_ids"], resolves=p["resolves"], updated_at=func.now()))
                updated += 1
        elif p["action_key"] not in done_keys:
            conn.execute(insert(actions), {**p, "status": "open"})
            created += 1
    for stale in open_by_key.values():
        conn.execute(update(actions).where(actions.c.id == stale["id"]).values(status="superseded", updated_at=func.now()))
    return {"created": created, "updated": updated, "superseded": len(open_by_key)}


def recalculate(conn: Connection, rules: dict, as_of: date, trigger: str, trigger_ref: str | None, actor: str) -> dict:
    lock_recalculation(conn)
    version = current_data_version(conn)
    if version["vessels"] is None:
        return {"calc_id": None, "results": [], "actions": {}}
    results = score_fleet(load_current_frames(conn), rules, as_of, resolved_records(conn, rules, version))
    calc_id = str(uuid.uuid4())
    conn.execute(insert(risk_snapshots), [
        {
            "calc_id": calc_id, "vessel_id": r["vessel_id"], "as_of": as_of, "trigger": trigger,
            "trigger_ref": trigger_ref, "data_version": version, "score": r["score"], "band": r["band"],
            "confidence": r["confidence"], "confidence_reasons": r["confidence_reasons"],
            "components": r["components"], "overrides": r["overrides"], "drivers": r["drivers"],
        }
        for r in results
    ])
    action_summary = _sync_actions(conn, results, rules, version, as_of)
    log_event(conn, "recalculation", actor, {
        "calc_id": calc_id, "trigger": trigger, "trigger_ref": trigger_ref, "as_of": as_of.isoformat(),
        "data_version": version, "rules_version": rules.get("version"), "actions": action_summary,
    })
    return {"calc_id": calc_id, "results": results, "actions": action_summary}


def latest_calc_id(conn: Connection, before_id: int | None = None) -> str | None:
    query = select(risk_snapshots.c.calc_id).order_by(risk_snapshots.c.id.desc()).limit(1)
    if before_id is not None:
        query = query.where(risk_snapshots.c.id < before_id)
    return conn.execute(query).scalar()


def snapshots_for(conn: Connection, calc_id: str | None) -> list[dict]:
    if calc_id is None:
        return []
    rows = conn.execute(select(risk_snapshots).where(risk_snapshots.c.calc_id == calc_id)).mappings()
    return sorted((dict(r) for r in rows), key=lambda r: (-r["score"], r["vessel_id"]))


def ranking_changes(before: list[dict], after: list[dict]) -> list[dict]:
    old = {s["vessel_id"]: s for s in before}
    changes = []
    for s in after:
        prev = old.get(s["vessel_id"])
        if prev is None or prev["score"] != s["score"] or prev["band"] != s["band"]:
            changes.append({
                "vessel_id": s["vessel_id"],
                "before": None if prev is None else {"score": prev["score"], "band": prev["band"]},
                "after": {"score": s["score"], "band": s["band"]},
            })
    return changes


def readiness_text(before: dict, after: dict) -> str:
    return f"{before['band']} {before['score']:.0f} → {after['band']} {after['score']:.0f}"


def complete_action(conn: Connection, action_id: int, vessel_id: str, evidence: str, actor: str,
                    rules: dict, as_of: date) -> dict | None:
    lock_recalculation(conn)
    action = conn.execute(select(actions).where(actions.c.id == action_id, actions.c.vessel_id == vessel_id)
                          .with_for_update()).mappings().first()
    if action is None:
        return None
    if action["status"] != "open":
        raise ValueError(f"Action is {action['status']}, only open actions can be completed")

    before = next(s for s in snapshots_for(conn, latest_calc_id(conn)) if s["vessel_id"] == vessel_id)
    conn.execute(update(actions).where(actions.c.id == action_id).values(
        status="completed", completed_at=func.now(), completed_by=actor, completion_evidence=evidence,
        completed_data_version=current_data_version(conn), updated_at=func.now()))
    calc = recalculate(conn, rules, as_of, "action", str(action_id), actor)
    after = next(r for r in calc["results"] if r["vessel_id"] == vessel_id)

    readiness = {
        "before": {"score": before["score"], "band": before["band"]},
        "after": {"score": after["score"], "band": after["band"]},
        "text": readiness_text(before, after),
    }
    conn.execute(update(actions).where(actions.c.id == action_id).values(readiness=readiness))
    log_event(conn, "action_completed", actor, {"action_id": action_id, "vessel_id": vessel_id,
                                                "evidence": evidence, "readiness": readiness})
    return {"action_id": action_id, "readiness": readiness, "calc_id": calc["calc_id"]}
