import copy

import pytest

from app.actions import plan_actions
from app.scoring import prepare, score_fleet, vessel_facts

from .conftest import AS_OF


@pytest.fixture(scope="module")
def fleet(sample, rules):
    return {r["vessel_id"]: r for r in score_fleet(sample, rules, AS_OF)}


def feature(result, component, name):
    return result["components"][component]["features"][name]


def test_scores_are_bounded_and_add_up(fleet, rules):
    for r in fleet.values():
        assert 0 <= r["score"] <= 100
        assert r["score"] == pytest.approx(sum(c["points"] for c in r["components"].values()), abs=0.1)
        for name, c in r["components"].items():
            assert 0 <= c["points"] <= rules["components"][name]["max_points"]


def test_expected_bands_on_sample_fleet(fleet):
    assert fleet["V001"]["band"] == "High"
    assert fleet["V004"]["band"] == "High"
    for vid in ("V017", "V019", "V007", "V012"):
        assert fleet[vid]["band"] == "Medium", vid
    ranked = sorted(fleet.values(), key=lambda r: -r["score"])
    assert [r["vessel_id"] for r in ranked[:2]] == ["V001", "V004"]


def test_v001_overrides(fleet):
    ids = {o["id"] for o in fleet["V001"]["overrides"]}
    assert ids == {"recent_detention", "aged_open_deficiency", "senior_certification", "critical_overdue_cluster"}
    aged = next(o for o in fleet["V001"]["overrides"] if o["id"] == "aged_open_deficiency")
    assert aged["record_ids"] == ["DEF0010", "DEF0011", "DEF0012"]


def test_v004_override_is_detention_and_ecdis(fleet):
    overrides = fleet["V004"]["overrides"]
    assert {o["id"] for o in overrides} == {"recent_detention", "critical_overdue_cluster"}
    assert any("ECDIS" in o["text"] for o in overrides)


def test_only_detained_vessels_have_detention_override(fleet):
    detained = {vid for vid, r in fleet.items() if any(o["id"] == "recent_detention" for o in r["overrides"])}
    assert detained == {"V001", "V004"}


def test_critical_cluster_needs_repeat_failures(fleet):
    for vid in ("V007", "V008", "V015"):
        assert not any(o["id"] == "critical_overdue_cluster" for o in fleet[vid]["overrides"]), vid


def test_inspection_component(fleet):
    v1 = fleet["V001"]
    assert feature(v1, "inspection", "last_result")["value"] == 1.0
    assert feature(v1, "inspection", "prior_bad_outcomes")["record_ids"] == ["INS0003", "INS0004"]
    assert "3 → 6 → 9 → 10" in feature(v1, "inspection", "deficiency_trend")["detail"]


def test_deficiency_component(fleet):
    v1 = fleet["V001"]
    assert len(feature(v1, "deficiencies", "open_severity")["record_ids"]) == 10
    assert "'Fire pump pressure low' at 4 inspections" in feature(v1, "deficiencies", "recurring")["detail"]


def test_maintenance_component(fleet):
    v1 = fleet["V001"]
    assert "55%" in feature(v1, "maintenance", "pct_overdue")["detail"]
    assert "Emergency Generator failed 3 times" in feature(v1, "maintenance", "repeat_failures")["detail"]


def test_crew_component(fleet):
    v1 = fleet["V001"]
    assert feature(v1, "crew", "training_pending")["value"] == 2
    assert feature(v1, "crew", "stcw_expiring")["record_ids"] == ["C0001"]


def test_audit_component(fleet):
    assert feature(fleet["V013"], "audit", "overdue_findings")["value"] == 7


def test_drivers_are_top_three_with_records(fleet):
    for r in fleet.values():
        assert len(r["drivers"]) <= 3
        points = [d["points"] for d in r["drivers"]]
        assert points == sorted(points, reverse=True)
    assert all(d["record_ids"] for d in fleet["V001"]["drivers"])


def test_confidence_is_low_when_last_inspection_is_stale(fleet):
    reasons = fleet["V001"]["confidence_reasons"]
    assert fleet["V001"]["confidence"] == "Low"
    assert any(r["check"] == "stale_inspection" for r in reasons)


def test_confidence_high_when_inspection_recent(sample, rules):
    result = {r["vessel_id"]: r for r in score_fleet(sample, rules, AS_OF.replace(year=2025, month=8, day=1))}
    assert not any(r["check"] == "stale_inspection" for r in result["V001"]["confidence_reasons"])


def test_scoring_is_deterministic(sample, rules):
    assert score_fleet(sample, rules, AS_OF) == score_fleet(sample, rules, AS_OF)


def test_resolutions_only_move_the_resolved_vessel(sample, rules, fleet):
    resolved = {"deficiencies": {"DEF0010", "DEF0011", "DEF0012"}}
    after = {r["vessel_id"]: r for r in score_fleet(sample, rules, AS_OF, resolved)}
    assert after["V001"]["score"] < fleet["V001"]["score"]
    assert not any(o["id"] == "aged_open_deficiency" for o in after["V001"]["overrides"])
    for vid in fleet:
        if vid != "V001":
            assert after[vid]["score"] == fleet[vid]["score"], vid


def test_band_without_overrides_uses_thresholds(sample, rules):
    no_overrides = copy.deepcopy(rules)
    no_overrides["overrides"]["recent_detention"]["months"] = 0
    no_overrides["overrides"]["critical_overdue_cluster"]["min_overdue"] = 99
    result = {r["vessel_id"]: r for r in score_fleet(sample, no_overrides, AS_OF)}
    assert result["V004"]["overrides"] == []
    assert result["V004"]["band"] == "High"  # 60+ on points alone


def test_vessel_with_no_data_scores_zero(rules):
    data = prepare({"vessels": __import__("pandas").DataFrame([{
        "vessel_id": "V999", "imo_number": "9999999", "vessel_name": "MV Empty", "vessel_type": "Bulk Carrier",
        "build_year": 2020, "flag_state": "Malta"}])})
    [result] = score_fleet(data, rules, AS_OF)
    assert result["score"] == 0 and result["band"] == "Low"
    assert {r["check"] for r in result["confidence_reasons"]} == {"missing_source"}


def test_v001_actions(fleet, rules):
    planned = {a["rule_id"]: a for a in plan_actions(fleet["V001"], rules, AS_OF)}
    fire = planned["aged_fire_deficiency"]
    assert (fire["owner"], fire["deadline_days"]) == ("Technical", 7)
    assert fire["resolves"] == {"deficiencies": ["DEF0010", "DEF0011", "DEF0012"]}
    stcw = planned["senior_certification"]
    assert stcw["owner"] == "Crewing" and stcw["deadline_label"] == "Before next port"
    assert "critical_overdue_cluster" in planned


def test_v004_and_v013_actions(fleet, rules):
    v4 = {a["rule_id"] for a in plan_actions(fleet["V004"], rules, AS_OF)}
    assert "recurring_navigation" in v4
    v13 = {a["rule_id"]: a for a in plan_actions(fleet["V013"], rules, AS_OF)}
    assert v13["overdue_audit_findings"]["owner"] == "HSQE"
    assert v13["overdue_audit_findings"]["deadline_days"] == 30


def test_facts_expose_triggers(sample, rules):
    facts = vessel_facts("V004", prepare(sample), rules, AS_OF)
    subjects = {t.subject for t in facts.triggers if t.type == "recurring_deficiency"}
    assert {"Chart correction records incomplete", "ECDIS procedure not followed"} <= subjects
