"""Row schemas for the 8 CSV tables of the sample dataset specification."""

from dataclasses import dataclass
from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, model_validator


def _empty_to_none(value):
    return None if isinstance(value, str) and value.strip() == "" else value


OptionalDate = Annotated[date | None, BeforeValidator(_empty_to_none)]
VesselId = Annotated[str, Field(pattern=r"^V\d{3}$")]
InspectionId = Annotated[str, Field(pattern=r"^INS\d{4}$")]
Text = Annotated[str, Field(min_length=1)]

DEFICIENCY_CATEGORIES = (
    "Fire Safety", "Navigation", "Life Saving", "Machinery", "ISM", "Pollution Prevention", "Structural",
)


class Row(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="ignore")


class VesselRow(Row):
    vessel_id: VesselId
    imo_number: Annotated[str, Field(pattern=r"^\d{7}$")]
    vessel_name: Text
    vessel_type: Text
    build_year: Annotated[int, Field(ge=1950, le=2100)]
    flag_state: Text


class InspectionRow(Row):
    inspection_id: InspectionId
    vessel_id: VesselId
    inspection_date: date
    inspection_port: Text
    inspection_authority: Text
    inspection_type: Literal["PSC", "Class", "Flag State", "SIRE/CDI"]
    inspection_result: Literal["No Major Findings", "Deficiencies Found", "Major Deficiencies", "Detained"]
    detention_flag: Literal["Yes", "No"]

    @model_validator(mode="after")
    def _flag_matches_result(self):
        if (self.detention_flag == "Yes") != (self.inspection_result == "Detained"):
            raise ValueError("detention_flag must be 'Yes' exactly when inspection_result is 'Detained'")
        return self


class DeficiencyRow(Row):
    deficiency_id: Annotated[str, Field(pattern=r"^DEF\d{4}$")]
    inspection_id: InspectionId
    vessel_id: VesselId
    deficiency_code: Annotated[str, Field(pattern=r"^[A-Z]{2,4}-\d+$")]
    deficiency_category: Literal[DEFICIENCY_CATEGORIES]
    deficiency_description: Text
    deficiency_status: Literal["Open", "Closed"]
    deficiency_closed_date: OptionalDate = None

    @model_validator(mode="after")
    def _closed_date_matches_status(self):
        if (self.deficiency_status == "Closed") != (self.deficiency_closed_date is not None):
            raise ValueError("deficiency_closed_date is required for Closed deficiencies and must be empty for Open ones")
        return self


class DetentionRow(Row):
    inspection_id: InspectionId
    vessel_id: VesselId
    detention_date: date
    detention_reason: Text


class AuditFindingRow(Row):
    audit_id: Annotated[str, Field(pattern=r"^AUD\d{4}$")]
    vessel_id: VesselId
    audit_finding_description: Text
    audit_finding_status: Literal["Open", "Closed", "Overdue"]


class CrewRow(Row):
    crew_id: Annotated[str, Field(pattern=r"^C\d{4}$")]
    vessel_id: VesselId
    rank: Text
    join_date: date
    rank_experience_months: Annotated[int, Field(ge=0, le=600)]
    training_status: Literal["Compliant", "Pending"]
    stcw_status: Literal["Valid", "Expiring Soon", "Expired"]


class EquipmentFailureRow(Row):
    failure_id: Annotated[str, Field(pattern=r"^FAIL\d{4}$")]
    vessel_id: VesselId
    equipment_name: Text
    equipment_failure_date: date
    equipment_failure_description: Text


class MaintenanceRow(Row):
    maintenance_id: Annotated[str, Field(pattern=r"^MAIN\d{4}$")]
    vessel_id: VesselId
    maintenance_equipment_name: Text
    maintenance_due_date: date
    maintenance_completed_date: OptionalDate = None
    maintenance_status: Literal["Completed", "Open", "Overdue"]

    @model_validator(mode="after")
    def _completed_date_matches_status(self):
        if (self.maintenance_status == "Completed") != (self.maintenance_completed_date is not None):
            raise ValueError("maintenance_completed_date is required for Completed jobs and must be empty otherwise")
        return self


@dataclass(frozen=True)
class TableSpec:
    table: str
    file_stem: str
    key: str
    model: type[Row]

    @property
    def columns(self) -> list[str]:
        return list(self.model.model_fields)


TABLE_SPECS: dict[str, TableSpec] = {
    s.table: s
    for s in (
        TableSpec("vessels", "VesselMaster", "vessel_id", VesselRow),
        TableSpec("inspections", "Inspections", "inspection_id", InspectionRow),
        TableSpec("deficiencies", "Deficiencies", "deficiency_id", DeficiencyRow),
        TableSpec("detentions", "Detentions", "inspection_id", DetentionRow),
        TableSpec("audit_findings", "AuditFindings", "audit_id", AuditFindingRow),
        TableSpec("crew", "Crew", "crew_id", CrewRow),
        TableSpec("equipment_failures", "EquipmentFailures", "failure_id", EquipmentFailureRow),
        TableSpec("maintenance", "Maintenance", "maintenance_id", MaintenanceRow),
    )
}

LOAD_ORDER = list(TABLE_SPECS)


def spec_for_file(file_name: str) -> TableSpec | None:
    stem = file_name.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    stem = stem[:-4] if stem.lower().endswith(".csv") else stem
    normalized = stem.replace("_", "").replace(" ", "").lower()
    for spec in TABLE_SPECS.values():
        if normalized in (spec.file_stem.lower(), spec.table.replace("_", "")):
            return spec
    return None
