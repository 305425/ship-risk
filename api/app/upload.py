"""CSV upload: validation, diff against the current version, and versioned load."""

import hashlib
import io
import uuid
from dataclasses import dataclass, field
from datetime import date

import pandas as pd
from pydantic import ValidationError
from sqlalchemy import insert, select, text
from sqlalchemy.engine import Connection

from .db import DATA_TABLES, uploads
from .schemas import LOAD_ORDER, TABLE_SPECS, TableSpec, spec_for_file


@dataclass
class RowError:
    file: str
    row: int | None
    column: str | None
    value: str | None
    message: str

    def as_dict(self) -> dict:
        return self.__dict__.copy()


@dataclass
class ParsedFile:
    file_name: str
    spec: TableSpec | None
    sha256: str
    rows: list[dict] = field(default_factory=list)
    lines: list[int] = field(default_factory=list)
    errors: list[RowError] = field(default_factory=list)


class UploadRejected(Exception):
    def __init__(self, errors: list[RowError]):
        super().__init__(f"{len(errors)} validation error(s)")
        self.errors = errors


def _line(index: int) -> int:
    return index + 2  # header is line 1


def parse_file(file_name: str, content: bytes) -> ParsedFile:
    parsed = ParsedFile(file_name, spec_for_file(file_name), hashlib.sha256(content).hexdigest())
    if parsed.spec is None:
        known = ", ".join(f"{s.file_stem}.csv" for s in TABLE_SPECS.values())
        parsed.errors.append(RowError(file_name, None, None, None, f"Unknown file. Expected one of: {known}"))
        return parsed
    try:
        frame = pd.read_csv(io.StringIO(content.decode("utf-8-sig")), dtype=str, keep_default_na=False)
    except (UnicodeDecodeError, pd.errors.ParserError, pd.errors.EmptyDataError) as exc:
        parsed.errors.append(RowError(file_name, None, None, None, f"File is not a readable UTF-8 CSV: {exc}"))
        return parsed

    frame.columns = [c.strip() for c in frame.columns]
    missing = [c for c in parsed.spec.columns if c not in frame.columns]
    for column in missing:
        parsed.errors.append(RowError(file_name, None, column, None, "Required column is missing"))
    if missing:
        return parsed
    if frame.empty:
        parsed.errors.append(RowError(file_name, None, None, None, "File has no data rows"))
        return parsed

    seen: dict[str, int] = {}
    for index, record in enumerate(frame[parsed.spec.columns].to_dict("records")):
        line = _line(index)
        key = record[parsed.spec.key].strip()
        if key in seen:
            parsed.errors.append(
                RowError(file_name, line, parsed.spec.key, key, f"Duplicate {parsed.spec.key}, first seen on row {seen[key]}")
            )
            continue
        seen[key] = line
        try:
            row = parsed.spec.model(**record).model_dump()
        except ValidationError as exc:
            for err in exc.errors():
                column = str(err["loc"][0]) if err["loc"] else None
                value = record.get(column) if column else None
                parsed.errors.append(RowError(file_name, line, column, value, err["msg"]))
            continue
        parsed.rows.append(row)
        parsed.lines.append(line)
    return parsed


def load_current_rows(conn: Connection, table: str) -> list[dict]:
    return [dict(r._mapping) for r in conn.execute(text(f"SELECT * FROM current_{table}"))]


def _check_references(batch: dict[str, ParsedFile], conn: Connection) -> list[RowError]:
    """Cross-table checks: known vessels and inspections, using the batch where present, else the current version."""

    def rows_of(table: str) -> list[dict]:
        return batch[table].rows if table in batch else load_current_rows(conn, table)

    vessel_ids = {r["vessel_id"] for r in rows_of("vessels")}
    inspections = {r["inspection_id"]: r for r in rows_of("inspections")}
    errors: list[RowError] = []

    def check(table: str, rows: list[dict], lines: list[int | None], file_name: str) -> None:
        for row, line in zip(rows, lines):
            if table != "vessels" and row["vessel_id"] not in vessel_ids:
                errors.append(RowError(file_name, line, "vessel_id", row["vessel_id"], "Unknown vessel_id (not in VesselMaster)"))
            if table in ("deficiencies", "detentions"):
                inspection = inspections.get(row["inspection_id"])
                if inspection is None:
                    errors.append(RowError(file_name, line, "inspection_id", row["inspection_id"], "Unknown inspection_id (not in Inspections)"))
                elif inspection["vessel_id"] != row["vessel_id"]:
                    errors.append(RowError(
                        file_name, line, "vessel_id", row["vessel_id"],
                        f"Inspection {row['inspection_id']} belongs to {inspection['vessel_id']}",
                    ))
                elif table == "detentions" and inspection["detention_flag"] != "Yes":
                    errors.append(RowError(
                        file_name, line, "inspection_id", row["inspection_id"],
                        "Inspection is not flagged as a detention (detention_flag is not 'Yes')",
                    ))

    for table, parsed in batch.items():
        check(table, parsed.rows, parsed.lines, parsed.file_name)

    # Replacing a parent table must not leave rows in the current version of a child table pointing nowhere.
    if "vessels" in batch or "inspections" in batch:
        for table in LOAD_ORDER:
            if table == "vessels" or table in batch:
                continue
            if table not in ("deficiencies", "detentions") and "vessels" not in batch:
                continue
            current = load_current_rows(conn, table)
            label = f"{TABLE_SPECS[table].file_stem}.csv (current version)"
            check(table, current, [None] * len(current), label)
    return errors


def _normalize(row: dict, columns: list[str]) -> dict[str, str]:
    def norm(value) -> str:
        if value is None:
            return ""
        if isinstance(value, date):
            return value.isoformat()
        return str(value)

    return {c: norm(row.get(c)) for c in columns}


def diff_rows(spec: TableSpec, old: list[dict], new: list[dict]) -> dict:
    old_by_key = {r[spec.key]: _normalize(r, spec.columns) for r in old}
    new_by_key = {r[spec.key]: _normalize(r, spec.columns) for r in new}
    added = sorted(new_by_key.keys() - old_by_key.keys())
    removed = sorted(old_by_key.keys() - new_by_key.keys())
    changed = []
    for key in sorted(new_by_key.keys() & old_by_key.keys()):
        fields = {c: {"old": old_by_key[key][c], "new": new_by_key[key][c]} for c in spec.columns if old_by_key[key][c] != new_by_key[key][c]}
        if fields:
            changed.append({"key": key, "fields": fields})
    return {"added": added, "changed": changed, "removed": removed}


def validate_upload(conn: Connection, files: list[tuple[str, bytes]]) -> dict[str, ParsedFile]:
    if not files:
        raise UploadRejected([RowError("", None, None, None, "No files uploaded")])
    parsed_files = [parse_file(name, content) for name, content in files]
    errors = [e for p in parsed_files for e in p.errors]

    batch: dict[str, ParsedFile] = {}
    for parsed in parsed_files:
        if parsed.spec is None:
            continue
        if parsed.spec.table in batch:
            errors.append(RowError(parsed.file_name, None, None, None, f"More than one file for table {parsed.spec.table}"))
        batch[parsed.spec.table] = parsed
    if errors:
        raise UploadRejected(errors)

    errors = _check_references(batch, conn)
    if errors:
        raise UploadRejected(errors)
    return {t: batch[t] for t in LOAD_ORDER if t in batch}


def save_upload(conn: Connection, batch: dict[str, ParsedFile], uploaded_by: str) -> dict:
    """Store each file as a new version of its table. Runs inside the caller's transaction."""
    batch_id = str(uuid.uuid4())
    files = []
    for table, parsed in batch.items():
        spec = TABLE_SPECS[table]
        diff = diff_rows(spec, load_current_rows(conn, table), parsed.rows)
        upload_id = conn.execute(
            insert(uploads).returning(uploads.c.id),
            {
                "batch_id": batch_id,
                "table_name": table,
                "file_name": parsed.file_name,
                "uploaded_by": uploaded_by,
                "sha256": parsed.sha256,
                "row_count": len(parsed.rows),
                "rows_added": len(diff["added"]),
                "rows_changed": len(diff["changed"]),
                "rows_removed": len(diff["removed"]),
                "status": "index_pending",
            },
        ).scalar_one()
        conn.execute(insert(DATA_TABLES[table]), [{**row, "upload_id": upload_id} for row in parsed.rows])
        files.append({
            "upload_id": upload_id,
            "table": table,
            "file_name": parsed.file_name,
            "row_count": len(parsed.rows),
            "rows_added": len(diff["added"]),
            "rows_changed": len(diff["changed"]),
            "rows_removed": len(diff["removed"]),
        })
    return {"batch_id": batch_id, "files": files}


def upload_diff(conn: Connection, upload_id: int) -> dict | None:
    upload = conn.execute(select(uploads).where(uploads.c.id == upload_id)).mappings().first()
    if upload is None:
        return None
    table = DATA_TABLES[upload["table_name"]]
    spec = TABLE_SPECS[upload["table_name"]]
    previous_id = conn.execute(
        select(uploads.c.id)
        .where(uploads.c.table_name == upload["table_name"], uploads.c.id < upload_id)
        .order_by(uploads.c.id.desc())
        .limit(1)
    ).scalar()

    def rows_for(uid: int | None) -> list[dict]:
        if uid is None:
            return []
        return [dict(r._mapping) for r in conn.execute(select(table).where(table.c.upload_id == uid))]

    return {
        "upload": dict(upload),
        "previous_upload_id": previous_id,
        **diff_rows(spec, rows_for(previous_id), rows_for(upload_id)),
    }


def current_data_version(conn: Connection) -> dict[str, int | None]:
    rows = conn.execute(text("SELECT table_name, max(id) FROM uploads GROUP BY table_name")).all()
    found = {name: uid for name, uid in rows}
    return {t: found.get(t) for t in LOAD_ORDER}
