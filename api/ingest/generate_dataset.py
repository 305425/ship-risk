"""Build a larger training snapshot and a held-out verification round.

The original sample in data/ stays as it is. data/train is that sample plus 40
vessels and five inspection rounds. data/verify is each new vessel's sixth
inspection, which is not part of the training upload.
"""

from __future__ import annotations

import csv
import json
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "data"
TRAIN = ROOT / "data" / "train"
VERIFY = ROOT / "data" / "verify"

NEW_VESSELS = 40
FIRST_NEW = 21
ROUNDS = [
    date(2023, 3, 15),
    date(2023, 9, 15),
    date(2024, 3, 15),
    date(2024, 9, 15),
    date(2025, 3, 15),
    date(2025, 9, 15),
]
HOLDOUT_ROUND = 5

NAMES = [
    "Orion", "Pegasus", "Nimbus", "Cascade", "Harbor", "Keel", "Mariner", "Summit", "Beacon", "Cinder",
    "Drift", "Elm", "Fathom", "Gale", "Herald", "Iris", "Juniper", "Kestrel", "Lumen", "Mast",
    "North", "Osprey", "Pilot", "Quarry", "Reef", "Sparrow", "Tide", "Umber", "Vesper", "Willow",
    "Yarrow", "Zenith", "Amber", "Boreal", "Cedar", "Drake", "Ember", "Flint", "Grove", "Hearth",
]
TYPES = ["Bulk Carrier", "Oil Tanker", "Container Ship", "Chemical Tanker", "General Cargo"]
FLAGS = ["Panama", "Liberia", "Marshall Islands", "Singapore", "Hong Kong"]
PORTS = ["Hamburg", "Shanghai", "Singapore", "Rotterdam", "Fujairah"]
AUTHORITIES = ["USCG", "Tokyo MOU", "Flag State", "Paris MOU"]
INSPECTION_TYPES = ["PSC", "Class", "Flag State", "SIRE/CDI"]
FIRE = "Fire pump pressure low"


def _profile(offset: int) -> str:
    if offset < 10:
        return "chronic"
    if offset < 20:
        return "emerging"
    if offset < 28:
        return "recovered"
    return "clean"


def _max_id(path: Path, column: str) -> int:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        return 0
    return max(int("".join(ch for ch in row[column] if ch.isdigit())) for row in rows)


def _read(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def _write(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _result(profile: str, round_index: int) -> str:
    if profile == "chronic":
        return ["Deficiencies Found", "Deficiencies Found", "Deficiencies Found", "Major Deficiencies", "Detained", "Detained"][round_index]
    if profile == "emerging":
        return "Major Deficiencies" if round_index == HOLDOUT_ROUND else "Deficiencies Found"
    if profile == "recovered":
        return "Major Deficiencies" if round_index == 2 else ("Deficiencies Found" if round_index < 2 else "No Major Findings")
    return "No Major Findings"


def _deficiencies(profile: str, round_index: int) -> list[tuple[str, str, str | None]]:
    """(category, description, days-until-closed or None when it stays open)."""
    if profile == "chronic":
        if round_index == 0:
            return [("Fire Safety", FIRE, 20), ("Fire Safety", "Fire alarm malfunction", 30)]
        return [("Fire Safety", FIRE, None), ("Machinery", "Emergency generator starting failure", None)]
    if profile == "emerging":
        count = [1, 2, 2, 3, 3, 3][round_index]
        rows = [("Fire Safety", FIRE, None)]
        if count > 1:
            rows.append(("Navigation", "Nautical publications missing", None))
        if count > 2:
            rows.append(("Life Saving", "Lifeboat engine not starting", None))
        if round_index == 0:
            return [("Fire Safety", FIRE, 25)]
        return rows
    if profile == "recovered":
        if round_index < 3:
            close = 40 if round_index < 2 else 30
            return [("Fire Safety", FIRE, close), ("ISM", "Risk assessment incomplete", close)]
        return []
    if round_index == 1:
        return [("Structural", "Minor hull coating damage", 20)]
    return []


def generate() -> dict:
    counters = {
        "inspection_id": _max_id(SOURCE / "Inspections.csv", "inspection_id"),
        "deficiency_id": _max_id(SOURCE / "Deficiencies.csv", "deficiency_id"),
        "crew_id": _max_id(SOURCE / "Crew.csv", "crew_id"),
        "maintenance_id": _max_id(SOURCE / "Maintenance.csv", "maintenance_id"),
    }

    def next_id(kind: str, prefix: str, width: int) -> str:
        counters[kind] += 1
        return f"{prefix}{counters[kind]:0{width}d}"

    tables = {name: _read(SOURCE / f"{name}.csv") for name in (
        "VesselMaster", "Inspections", "Deficiencies", "Detentions", "AuditFindings", "Crew", "EquipmentFailures", "Maintenance",
    )}
    verify_inspections: list[dict[str, str]] = []
    verify_deficiencies: list[dict[str, str]] = []
    verify_detentions: list[dict[str, str]] = []
    manifest: list[dict] = []

    for offset in range(NEW_VESSELS):
        profile = _profile(offset)
        vessel_id = f"V{FIRST_NEW + offset:03d}"
        tables["VesselMaster"][1].append({
            "vessel_id": vessel_id,
            "imo_number": f"{9800000 + FIRST_NEW + offset}",
            "vessel_name": f"MV {NAMES[offset]}",
            "vessel_type": TYPES[offset % len(TYPES)],
            "build_year": str(2004 + (offset % 16)),
            "flag_state": FLAGS[offset % len(FLAGS)],
        })
        tables["Crew"][1].append({
            "crew_id": next_id("crew_id", "C", 4),
            "vessel_id": vessel_id,
            "rank": "Master",
            "join_date": "2026-01-15",
            "rank_experience_months": "96" if profile == "clean" else "18",
            "training_status": "Compliant" if profile == "clean" else "Pending",
            "stcw_status": "Valid" if profile != "chronic" else "Expiring Soon",
        })
        overdue = profile in ("chronic", "emerging")
        tables["Maintenance"][1].append({
            "maintenance_id": next_id("maintenance_id", "MAIN", 4),
            "vessel_id": vessel_id,
            "maintenance_equipment_name": "Fire Pump",
            "maintenance_due_date": "2026-08-01",
            "maintenance_completed_date": "" if overdue else "2026-07-20",
            "maintenance_status": "Overdue" if overdue else "Completed",
        })

        for round_index, inspected in enumerate(ROUNDS):
            result = _result(profile, round_index)
            inspection_id = next_id("inspection_id", "INS", 4)
            inspection = {
                "inspection_id": inspection_id,
                "vessel_id": vessel_id,
                "inspection_date": inspected.isoformat(),
                "inspection_port": PORTS[(offset + round_index) % len(PORTS)],
                "inspection_authority": AUTHORITIES[(offset + round_index) % len(AUTHORITIES)],
                "inspection_type": INSPECTION_TYPES[(offset + round_index) % len(INSPECTION_TYPES)],
                "inspection_result": result,
                "detention_flag": "Yes" if result == "Detained" else "No",
            }
            deficiencies = []
            for category, description, close_in in _deficiencies(profile, round_index):
                closed = ""
                status = "Open"
                if close_in is not None:
                    status = "Closed"
                    closed = (inspected + timedelta(days=close_in)).isoformat()
                deficiencies.append({
                    "deficiency_id": next_id("deficiency_id", "DEF", 4),
                    "inspection_id": inspection_id,
                    "vessel_id": vessel_id,
                    "deficiency_code": "FIR-20" if category == "Fire Safety" else "NAV-10",
                    "deficiency_category": category,
                    "deficiency_description": description,
                    "deficiency_status": status,
                    "deficiency_closed_date": closed,
                })
            detention = None
            if result == "Detained":
                detention = {
                    "inspection_id": inspection_id,
                    "vessel_id": vessel_id,
                    "detention_date": inspected.isoformat(),
                    "detention_reason": "Repeated fire safety deficiencies",
                }
            if round_index == HOLDOUT_ROUND:
                verify_inspections.append(inspection)
                verify_deficiencies.extend(deficiencies)
                if detention:
                    verify_detentions.append(detention)
                manifest.append({
                    "vessel_id": vessel_id,
                    "vessel_name": f"MV {NAMES[offset]}",
                    "profile": profile,
                    "inspection_id": inspection_id,
                    "inspection_date": inspected.isoformat(),
                    "outcome": result,
                    "label": int(result in ("Major Deficiencies", "Detained")),
                })
                continue
            tables["Inspections"][1].append(inspection)
            tables["Deficiencies"][1].extend(deficiencies)
            if detention:
                tables["Detentions"][1].append(detention)

    for name, (fields, rows) in tables.items():
        _write(TRAIN / f"{name}.csv", fields, rows)
    _write(VERIFY / "Inspections.csv", tables["Inspections"][0], verify_inspections)
    _write(VERIFY / "Deficiencies.csv", tables["Deficiencies"][0], verify_deficiencies)
    _write(VERIFY / "Detentions.csv", tables["Detentions"][0], verify_detentions)
    (VERIFY / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    summary = {
        "vessels": len(tables["VesselMaster"][1]),
        "training_inspections": len(tables["Inspections"][1]),
        "training_deficiencies": len(tables["Deficiencies"][1]),
        "holdout_inspections": len(verify_inspections),
        "holdout_bad": sum(item["label"] for item in manifest),
    }
    print(json.dumps(summary))
    return summary


if __name__ == "__main__":
    generate()
