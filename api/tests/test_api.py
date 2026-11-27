import pytest

pytestmark = pytest.mark.db


def upload(client, files):
    return client.post("/api/upload", files=[("files", (name, content, "text/csv")) for name, content in files])


@pytest.fixture
def loaded(client, sample_files):
    response = upload(client, sample_files)
    assert response.status_code == 200, response.text
    return client


def test_health_needs_no_key(client):
    response = client.get("/api/health", headers={"X-API-Key": ""})
    assert response.status_code == 200
    assert response.json()["postgres"] == "up"


def test_endpoints_require_api_key(client):
    assert client.get("/api/fleet/ranking", headers={"X-API-Key": "wrong"}).status_code == 401
    assert client.post("/api/upload", headers={"X-API-Key": "wrong"}, files=[("files", ("a.csv", b"x"))]).status_code == 401


def test_sample_upload_loads_all_tables(loaded):
    counts = {u["table_name"]: u["row_count"] for u in loaded.get("/api/uploads").json()}
    assert counts == {"vessels": 20, "inspections": 80, "deficiencies": 286, "detentions": 2,
                      "audit_findings": 135, "crew": 240, "equipment_failures": 157, "maintenance": 400}


def test_ranking_and_vessel_endpoints(loaded):
    ranking = loaded.get("/api/fleet/ranking").json()
    assert len(ranking) == 20
    assert [r["vessel_id"] for r in ranking[:2]] == ["V001", "V004"]
    risk = loaded.get("/api/vessels/V001/risk").json()
    assert risk["band"] == "High" and set(risk["components"]) == {"inspection", "deficiencies", "maintenance", "crew", "audit"}
    issues = loaded.get("/api/vessels/V001/issues").json()
    assert len(issues["open_deficiencies"]) == 10
    assert loaded.get("/api/vessels/V999/risk").status_code == 404


def test_risk_model_endpoint_leaves_the_rule_band(loaded):
    body = loaded.get("/api/risk-model").json()
    assert body["model"] == "logistic_regression" and body["role"] == "shadow"
    assert body["registry"]["name"] == "ship-risk-shadow" and int(body["registry"]["version"]) >= 1
    assert [row["vessel_id"] for row in body["current"][:2]] == ["V001", "V004"]
    ranking = loaded.get("/api/fleet/ranking").json()
    assert [row["vessel_id"] for row in ranking[:2]] == ["V001", "V004"]
    assert ranking[0]["band"] == "High"


def test_backtest_endpoint(loaded):
    body = loaded.get("/api/backtest?top_n=3").json()
    assert body["summary"]["recall"] == 1.0
    assert len(body["bad_outcomes"]) == 3 and body["caveats"]
    assert loaded.get("/api/backtest?top_n=0").status_code == 422


def test_broken_upload_is_rejected_and_nothing_saved(loaded):
    before = loaded.get("/api/uploads").json()
    bad_maintenance = (
        b"maintenance_id,vessel_id,maintenance_equipment_name,maintenance_due_date,maintenance_completed_date,maintenance_status\n"
        b"MAIN0001,V777,Fire Pump,2026-07-05,,Overdue\n"
        b"MAIN0002,V001,Fire Pump,not-a-date,,Overdue\n"
    )
    missing_column = b"crew_id,vessel_id\nC0001,V001\n"
    response = upload(loaded, [("Maintenance.csv", bad_maintenance), ("Crew.csv", missing_column)])
    assert response.status_code == 422
    errors = response.json()["errors"]
    assert any(e["file"] == "Maintenance.csv" and e["row"] == 3 and e["column"] == "maintenance_due_date" for e in errors)
    assert any(e["file"] == "Crew.csv" and e["column"] == "rank" for e in errors)
    assert loaded.get("/api/uploads").json() == before


def test_unknown_vessel_is_rejected(loaded):
    body = (
        b"maintenance_id,vessel_id,maintenance_equipment_name,maintenance_due_date,maintenance_completed_date,maintenance_status\n"
        b"MAIN0001,V777,Fire Pump,2026-07-05,,Overdue\n"
    )
    errors = upload(loaded, [("Maintenance.csv", body)]).json()["errors"]
    assert errors[0]["column"] == "vessel_id" and "Unknown vessel_id" in errors[0]["message"]


def test_changed_maintenance_upload_shows_diff_and_ranking_change(loaded, sample_files):
    original = dict(sample_files)["Maintenance.csv"].decode()
    lines = original.splitlines()
    changed = [lines[0]]
    for line in lines[1:]:
        if line.startswith(("MAIN0001,", "MAIN0003,", "MAIN0005,", "MAIN0009,")):  # V001 Emergency Generator jobs
            parts = line.split(",")
            parts[4], parts[5] = parts[3], "Completed"
            line = ",".join(parts)
        changed.append(line)
    response = upload(loaded, [("Maintenance.csv", ("\n".join(changed) + "\n").encode())])
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["files"][0]["rows_changed"] == 4
    assert any(c["vessel_id"] == "V001" for c in body["ranking_changes"])

    diff = loaded.get(f"/api/uploads/{body['files'][0]['upload_id']}/diff").json()
    assert sorted(c["key"] for c in diff["changed"]) == ["MAIN0001", "MAIN0003", "MAIN0005", "MAIN0009"]
    assert diff["added"] == [] and diff["removed"] == []
    v001 = next(c for c in diff["ranking_changes"] if c["vessel_id"] == "V001")
    assert v001["after"]["score"] < v001["before"]["score"]


def test_reupload_unchanged_creates_no_diff_or_duplicate_actions(loaded, sample_files):
    actions_before = loaded.get("/api/vessels/V001/actions").json()
    body = upload(loaded, sample_files).json()
    assert all(f["rows_added"] == f["rows_changed"] == f["rows_removed"] == 0 for f in body["files"])
    assert body["ranking_changes"] == []
    assert loaded.get("/api/vessels/V001/actions").json() == actions_before


def test_v001_actions_and_readiness(loaded):
    actions = {a["rule_id"]: a for a in loaded.get("/api/vessels/V001/actions").json()}
    fire = actions["aged_fire_deficiency"]
    assert fire["owner"] == "Technical" and fire["deadline_days"] == 7
    assert actions["senior_certification"]["owner"] == "Crewing"

    response = loaded.post(f"/api/vessels/V001/actions/{fire['id']}/complete",
                           json={"evidence": "Fire pump overhauled and pressure-tested, report FP-2026-11"})
    assert response.status_code == 200, response.text
    readiness = response.json()["readiness"]
    assert readiness["after"]["score"] < readiness["before"]["score"]
    assert "→" in readiness["text"]

    risk = loaded.get("/api/vessels/V001/risk").json()
    assert not any(o["id"] == "aged_open_deficiency" for o in risk["overrides"])
    assert risk["trigger"] == "action"
    open_ids = {a["rule_id"] for a in loaded.get("/api/vessels/V001/actions").json()}
    assert "aged_fire_deficiency" not in open_ids

    again = loaded.post(f"/api/vessels/V001/actions/{fire['id']}/complete", json={"evidence": "again"})
    assert again.status_code == 409


def test_record_lookup_returns_the_current_row(loaded):
    inspection = loaded.get("/api/records/INS0001").json()
    assert inspection["kind"] == "Inspection"
    assert inspection["evidence_id"] == "inspections:INS0001"
    assert inspection["vessel_id"] == "V001"
    assert inspection["vessel_name"] == "MV Alpha"
    fields = {field["name"]: field["value"] for field in inspection["fields"]}
    assert fields["Inspection date"] == "2024-02-15"
    assert fields["Inspection result"] == "Deficiencies Found"

    maintenance = loaded.get("/api/records/maintenance:MAIN0001").json()
    assert maintenance["kind"] == "Maintenance" and maintenance["record_id"] == "MAIN0001"
    report = loaded.get("/api/records/report:INS0001").json()
    assert report["evidence_id"] == inspection["evidence_id"]
    assert loaded.get("/api/records/NOPE").status_code == 404
    assert loaded.get("/api/records/INS0001", headers={"X-API-Key": "wrong"}).status_code == 401


def test_new_upload_of_resolved_table_reopens_action(loaded, sample_files):
    fire = next(a for a in loaded.get("/api/vessels/V001/actions").json() if a["rule_id"] == "aged_fire_deficiency")
    loaded.post(f"/api/vessels/V001/actions/{fire['id']}/complete", json={"evidence": "Fixed"})
    upload(loaded, [("Deficiencies.csv", dict(sample_files)["Deficiencies.csv"])])
    open_ids = {a["rule_id"] for a in loaded.get("/api/vessels/V001/actions").json()}
    assert "aged_fire_deficiency" in open_ids
