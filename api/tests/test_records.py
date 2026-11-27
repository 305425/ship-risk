from app.main import app
from app.records import parse_evidence_id


def test_parse_bare_ids_and_evidence_ids():
    assert parse_evidence_id("INS0001") == ("inspections", "INS0001")
    assert parse_evidence_id("main0004") == ("maintenance", "MAIN0004")
    assert parse_evidence_id("maintenance:MAIN0001") == ("maintenance", "MAIN0001")
    assert parse_evidence_id("report:INS0086") == ("inspections", "INS0086")
    assert parse_evidence_id("summary:V021") == ("vessels", "V021")
    assert parse_evidence_id("C0012") == ("crew", "C0012")
    assert parse_evidence_id("not-a-record") is None


def test_openapi_publishes_swagger_and_the_api_key():
    schema = app.openapi()
    assert "/api/health" in schema["paths"]
    assert "/api/fleet/ranking" in schema["paths"]
    assert "/api/records/{record_id}" in schema["paths"]
    schemes = schema["components"]["securitySchemes"]
    assert schemes["API key"]["type"] == "apiKey"
    assert schemes["API key"]["name"] == "X-API-Key"
    assert schemes["API key"]["in"] == "header"
