from app.schemas import spec_for_file
from app.upload import diff_rows, parse_file

HEADER = "maintenance_id,vessel_id,maintenance_equipment_name,maintenance_due_date,maintenance_completed_date,maintenance_status\n"


def test_sample_files_parse_without_errors(sample_files):
    for name, content in sample_files:
        parsed = parse_file(name, content)
        assert parsed.errors == [], (name, parsed.errors[:3])
        assert len(parsed.rows) == content.decode("utf-8-sig").strip().count("\n")


def test_file_names_map_to_tables():
    assert spec_for_file("VesselMaster.csv").table == "vessels"
    assert spec_for_file("equipment_failures.csv").table == "equipment_failures"
    assert spec_for_file("notes.txt") is None


def test_unknown_file_is_rejected():
    parsed = parse_file("Weather.csv", b"a,b\n1,2\n")
    assert "Unknown file" in parsed.errors[0].message


def test_missing_column_is_reported():
    parsed = parse_file("Maintenance.csv", b"maintenance_id,vessel_id\nMAIN0001,V001\n")
    missing = {e.column for e in parsed.errors}
    assert {"maintenance_due_date", "maintenance_status"} <= missing


def test_bad_values_are_reported_per_row():
    body = HEADER + (
        "MAIN0001,V001,Fire Pump,2026-13-40,,Overdue\n"
        "MAIN0002,V1,Fire Pump,2026-07-05,,Overdue\n"
        "MAIN0003,V001,Fire Pump,2026-07-05,,Late\n"
        "MAIN0004,V001,Fire Pump,2026-07-05,,Completed\n"
        "MAIN0004,V001,Fire Pump,2026-07-05,,Open\n"
    )
    parsed = parse_file("Maintenance.csv", body.encode())
    by_row = {(e.row, e.column) for e in parsed.errors}
    assert (2, "maintenance_due_date") in by_row
    assert (3, "vessel_id") in by_row
    assert (4, "maintenance_status") in by_row
    assert any(e.row == 5 and "completed_date" in e.message for e in parsed.errors)
    assert any(e.row == 6 and "Duplicate" in e.message for e in parsed.errors)


def test_inspection_detention_flag_must_match_result():
    body = (
        "inspection_id,vessel_id,inspection_date,inspection_port,inspection_authority,inspection_type,inspection_result,detention_flag\n"
        "INS0001,V001,2024-02-15,Hamburg,USCG,PSC,Detained,No\n"
    )
    parsed = parse_file("Inspections.csv", body.encode())
    assert "detention_flag" in parsed.errors[0].message


def test_diff_detects_added_changed_removed(sample_files):
    from app.schemas import TABLE_SPECS

    content = dict(sample_files)["Maintenance.csv"]
    old = parse_file("Maintenance.csv", content).rows
    new = [dict(r) for r in old[1:]]
    new[0]["maintenance_status"] = "Completed"
    new[0]["maintenance_completed_date"] = new[0]["maintenance_due_date"]
    new.append({**old[0], "maintenance_id": "MAIN9999"})
    diff = diff_rows(TABLE_SPECS["maintenance"], old, new)
    assert diff["added"] == ["MAIN9999"]
    assert diff["removed"] == [old[0]["maintenance_id"]]
    assert [c["key"] for c in diff["changed"]] == [new[0]["maintenance_id"]]
