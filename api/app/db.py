from functools import lru_cache

from sqlalchemy import (
    JSON,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
    func,
)
from sqlalchemy.engine import Engine

from .config import get_settings

metadata = MetaData()


def _upload_fk() -> Column:
    return Column("upload_id", Integer, ForeignKey("uploads.id"), primary_key=True)


uploads = Table(
    "uploads",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("batch_id", String(36), nullable=False, index=True),
    Column("table_name", String(40), nullable=False, index=True),
    Column("file_name", String(255), nullable=False),
    Column("uploaded_by", String(100), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("sha256", String(64), nullable=False),
    Column("row_count", Integer, nullable=False),
    Column("rows_added", Integer, nullable=False),
    Column("rows_changed", Integer, nullable=False),
    Column("rows_removed", Integer, nullable=False),
    Column("status", String(20), nullable=False),
)

vessels = Table(
    "vessels",
    metadata,
    _upload_fk(),
    Column("vessel_id", String(10), primary_key=True),
    Column("imo_number", String(7), nullable=False),
    Column("vessel_name", String(100), nullable=False),
    Column("vessel_type", String(50), nullable=False),
    Column("build_year", Integer, nullable=False),
    Column("flag_state", String(50), nullable=False),
)

inspections = Table(
    "inspections",
    metadata,
    _upload_fk(),
    Column("inspection_id", String(20), primary_key=True),
    Column("vessel_id", String(10), nullable=False),
    Column("inspection_date", Date, nullable=False),
    Column("inspection_port", String(100), nullable=False),
    Column("inspection_authority", String(100), nullable=False),
    Column("inspection_type", String(30), nullable=False),
    Column("inspection_result", String(30), nullable=False),
    Column("detention_flag", String(3), nullable=False),
)

deficiencies = Table(
    "deficiencies",
    metadata,
    _upload_fk(),
    Column("deficiency_id", String(20), primary_key=True),
    Column("inspection_id", String(20), nullable=False),
    Column("vessel_id", String(10), nullable=False),
    Column("deficiency_code", String(20), nullable=False),
    Column("deficiency_category", String(40), nullable=False),
    Column("deficiency_description", Text, nullable=False),
    Column("deficiency_status", String(10), nullable=False),
    Column("deficiency_closed_date", Date),
)

detentions = Table(
    "detentions",
    metadata,
    _upload_fk(),
    Column("inspection_id", String(20), primary_key=True),
    Column("vessel_id", String(10), nullable=False),
    Column("detention_date", Date, nullable=False),
    Column("detention_reason", Text, nullable=False),
)

audit_findings = Table(
    "audit_findings",
    metadata,
    _upload_fk(),
    Column("audit_id", String(20), primary_key=True),
    Column("vessel_id", String(10), nullable=False),
    Column("audit_finding_description", Text, nullable=False),
    Column("audit_finding_status", String(10), nullable=False),
)

crew = Table(
    "crew",
    metadata,
    _upload_fk(),
    Column("crew_id", String(20), primary_key=True),
    Column("vessel_id", String(10), nullable=False),
    Column("rank", String(40), nullable=False),
    Column("join_date", Date, nullable=False),
    Column("rank_experience_months", Integer, nullable=False),
    Column("training_status", String(20), nullable=False),
    Column("stcw_status", String(20), nullable=False),
)

equipment_failures = Table(
    "equipment_failures",
    metadata,
    _upload_fk(),
    Column("failure_id", String(20), primary_key=True),
    Column("vessel_id", String(10), nullable=False),
    Column("equipment_name", String(60), nullable=False),
    Column("equipment_failure_date", Date, nullable=False),
    Column("equipment_failure_description", Text, nullable=False),
)

maintenance = Table(
    "maintenance",
    metadata,
    _upload_fk(),
    Column("maintenance_id", String(20), primary_key=True),
    Column("vessel_id", String(10), nullable=False),
    Column("maintenance_equipment_name", String(60), nullable=False),
    Column("maintenance_due_date", Date, nullable=False),
    Column("maintenance_completed_date", Date),
    Column("maintenance_status", String(12), nullable=False),
)

risk_snapshots = Table(
    "risk_snapshots",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("calc_id", String(36), nullable=False, index=True),
    Column("vessel_id", String(10), nullable=False, index=True),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("as_of", Date, nullable=False),
    Column("trigger", String(20), nullable=False),
    Column("trigger_ref", String(64)),
    Column("data_version", JSON, nullable=False),
    Column("score", Float, nullable=False),
    Column("band", String(10), nullable=False),
    Column("confidence", String(10), nullable=False),
    Column("confidence_reasons", JSON, nullable=False),
    Column("components", JSON, nullable=False),
    Column("overrides", JSON, nullable=False),
    Column("drivers", JSON, nullable=False),
)

actions = Table(
    "actions",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("vessel_id", String(10), nullable=False, index=True),
    Column("rule_id", String(60), nullable=False),
    Column("action_key", String(200), nullable=False, index=True),
    Column("text", Text, nullable=False),
    Column("owner", String(30), nullable=False),
    Column("deadline_days", Integer, nullable=False),
    Column("deadline_label", String(60)),
    Column("due_date", Date, nullable=False),
    Column("record_ids", JSON, nullable=False),
    Column("resolves", JSON, nullable=False),
    Column("status", String(20), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("completed_at", DateTime(timezone=True)),
    Column("completed_by", String(100)),
    Column("completion_evidence", Text),
    Column("completed_data_version", JSON),
    Column("readiness", JSON),
)

audit_log = Table(
    "audit_log",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("event_type", String(40), nullable=False, index=True),
    Column("actor", String(100), nullable=False),
    Column("details", JSON, nullable=False),
)

DATA_TABLES: dict[str, Table] = {
    t.name: t
    for t in (vessels, inspections, deficiencies, detentions, audit_findings, crew, equipment_failures, maintenance)
}


@lru_cache
def get_engine() -> Engine:
    return create_engine(get_settings().database_url, pool_pre_ping=True)
