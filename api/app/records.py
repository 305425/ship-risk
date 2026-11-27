"""Look up one current CSV row by its id or evidence id."""

from datetime import date, datetime

from sqlalchemy import text
from sqlalchemy.engine import Connection

from .schemas import TABLE_SPECS

KIND = {
    "vessels": "Vessel",
    "inspections": "Inspection",
    "deficiencies": "Deficiency",
    "detentions": "Detention",
    "audit_findings": "Audit finding",
    "crew": "Crew",
    "equipment_failures": "Equipment failure",
    "maintenance": "Maintenance",
}

# Longer prefixes first so MAIN is not read as something else and C is not part of a longer code.
_PREFIXES = (
    ("MAIN", "maintenance"),
    ("FAIL", "equipment_failures"),
    ("INS", "inspections"),
    ("DEF", "deficiencies"),
    ("AUD", "audit_findings"),
    ("C", "crew"),
    ("V", "vessels"),
)

_ALIASES = {
    "vessel": "vessels",
    "vessels": "vessels",
    "inspection": "inspections",
    "inspections": "inspections",
    "report": "inspections",
    "deficiency": "deficiencies",
    "deficiencies": "deficiencies",
    "detention": "detentions",
    "detentions": "detentions",
    "audit": "audit_findings",
    "audit_findings": "audit_findings",
    "crew": "crew",
    "equipment": "equipment_failures",
    "equipment_failures": "equipment_failures",
    "failure": "equipment_failures",
    "maintenance": "maintenance",
    "summary": "vessels",
}


def parse_evidence_id(raw: str) -> tuple[str, str] | None:
    """Return (table, record id) for a bare id or an evidence id such as maintenance:MAIN0001."""
    text_id = raw.strip()
    if ":" in text_id:
        prefix, record_id = text_id.split(":", 1)
        table = _ALIASES.get(prefix.strip().lower())
        record_id = record_id.strip()
        if table and record_id:
            return table, record_id
        return None
    upper = text_id.upper()
    for prefix, table in _PREFIXES:
        if upper.startswith(prefix) and upper[len(prefix):].isdigit():
            return table, upper
    return None


def _value(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return value


def _label(column: str) -> str:
    return column.replace("_", " ").capitalize()


def find_record(conn: Connection, raw_id: str) -> dict | None:
    parsed = parse_evidence_id(raw_id)
    if parsed is None:
        return None
    table, record_id = parsed
    spec = TABLE_SPECS[table]
    row = conn.execute(
        text(f"SELECT * FROM current_{table} WHERE {spec.key} = :record_id"),
        {"record_id": record_id},
    ).mappings().first()
    if row is None:
        return None
    fields = [
        {"name": _label(column), "value": _value(row[column])}
        for column in spec.columns
        if column in row
    ]
    vessel_id = row.get("vessel_id")
    vessel_name = None
    if vessel_id:
        name = conn.execute(
            text("SELECT vessel_name FROM current_vessels WHERE vessel_id = :vessel_id"),
            {"vessel_id": vessel_id},
        ).scalar()
        vessel_name = name
    return {
        "evidence_id": f"{table}:{record_id}",
        "table": table,
        "kind": KIND[table],
        "record_id": record_id,
        "vessel_id": vessel_id,
        "vessel_name": vessel_name,
        "fields": fields,
    }
