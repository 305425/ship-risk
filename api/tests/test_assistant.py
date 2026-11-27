import pytest

from app.assistant import fleet_template, open_items, other_vessels, run_fleet

pytestmark = pytest.mark.db


def test_other_vessel_mentions_are_detected():
    assert other_vessels("Why was V004 detained?", "V001") == ["V004"]
    assert other_vessels("How many overdue jobs does V001 have?", "V001") == []
    assert other_vessels("What fire pump problems has this vessel had?", "V001") == []


def test_open_item_counts_match_the_database(client, sample_files):
    from tests.test_api import upload

    assert upload(client, sample_files).status_code == 200
    items = open_items("V001")
    overdue = items["overdue_maintenance"]
    assert overdue["count"] == 11
    assert len(overdue["items"]) <= 12
    assert all(item["maintenance_id"].startswith("MAIN") for item in overdue["items"])
    assert items["open_deficiencies"]["count"] == 10


def test_ask_about_another_vessel_is_refused(client, sample_files):
    from tests.test_api import upload

    assert upload(client, sample_files).status_code == 200
    response = client.post("/api/vessels/V001/ask", json={"question": "Why was V004 detained?"})
    assert response.status_code == 200
    body = response.json()
    assert body["refused"] is True
    assert body["tools"] == []
    assert "V004" in body["answer"] and "V001" in body["answer"]


def test_fleet_chat_lists_every_vessel_without_a_model(client, sample_files):
    from tests.test_api import upload

    assert upload(client, sample_files).status_code == 200
    body = run_fleet("Which vessels are high risk?", "test")
    assert body["mode"] == "template" and body["refused"] is False
    assert "V001" in body["answer"] and "V004" in body["answer"] and "V013" in body["answer"]
    assert "V001" in fleet_template()


def test_ask_without_a_model_uses_the_template(client, sample_files):
    from tests.test_api import upload

    assert upload(client, sample_files).status_code == 200
    body = client.post("/api/vessels/V001/ask", json={"question": "What is the risk score?"}).json()
    assert body["mode"] == "template"
    assert body["model"] is None
    assert "V001" in body["answer"] and "High" in body["answer"]
