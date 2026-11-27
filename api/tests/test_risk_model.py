from datetime import date

import pytest

from app.risk_model import feature_columns, shadow_report, training_frame
from app.scoring import score_fleet

AS_OF = date(2026, 11, 25)


@pytest.fixture(scope="module")
def trained(sample, rules):
    return training_frame(sample, rules), shadow_report(sample, rules, AS_OF)


def test_training_rows_use_later_inspections_only(trained):
    frame, _report = trained
    assert len(frame) == 60
    assert int(frame["label"].sum()) == 3
    assert set(frame.loc[frame["label"] == 1, "inspection_id"]) == {"INS0003", "INS0004", "INS0016"}
    assert set(frame["round"]) == {2, 3, 4}


def test_features_match_the_rule_components(rules):
    assert feature_columns(rules) == [
        "inspection.last_result",
        "inspection.deficiency_trend",
        "inspection.prior_bad_outcomes",
        "deficiencies.open_severity",
        "deficiencies.open_age",
        "deficiencies.recurring",
    ]


def test_shadow_model_reports_every_check(trained):
    _frame, report = trained
    assert report["model"] == "logistic_regression"
    assert report["role"] == "shadow"
    assert report["rows"] == 60 and report["positives"] == 3
    assert {item["feature"] for item in report["coefficients"]} == set(report["features"])

    for check in ("in_sample", "forward", "leave_one_vessel_out"):
        outcomes = report[check]["bad_outcomes"]
        assert outcomes
        assert all(1 <= item["rank"] <= 20 for item in outcomes)
        assert all(0.0 <= item["probability"] <= 1.0 for item in outcomes)
        assert report[check]["recall_at_2"]["bad_outcomes"] == len(outcomes)

    assert {item["inspection_id"] for item in report["in_sample"]["bad_outcomes"]} == {"INS0003", "INS0004", "INS0016"}
    assert {item["inspection_id"] for item in report["forward"]["bad_outcomes"]} == {"INS0004", "INS0016"}
    assert report["forward"]["trained_on_rounds_before"] == 4
    in_sample = {item["inspection_id"]: item["rank"] for item in report["in_sample"]["bad_outcomes"]}
    forward = {item["inspection_id"]: item["rank"] for item in report["forward"]["bad_outcomes"]}
    held_out = {item["inspection_id"]: item["rank"] for item in report["leave_one_vessel_out"]["bad_outcomes"]}
    assert in_sample["INS0004"] == 1 and report["in_sample"]["recall_at_3"]["recall"] == 1.0
    assert forward["INS0004"] == 1 and forward["INS0016"] <= 5
    assert held_out["INS0003"] == 1 and held_out["INS0004"] == 1


def test_current_shadow_score_does_not_replace_the_rule_score(sample, rules, trained):
    before = score_fleet(sample, rules, AS_OF)
    report = trained[1]
    after = score_fleet(sample, rules, AS_OF)
    assert after == before

    official = {row["vessel_id"]: row for row in before}
    assert len(report["current"]) == 20
    assert [row["vessel_id"] for row in report["current"][:2]] == ["V001", "V004"]
    assert report["current"][0]["margin"] > report["current"][1]["margin"] > report["current"][2]["margin"]
    assert report["current"][0]["shadow_score"] == 100.0
    assert report["current"][-1]["shadow_score"] == 0.0
    for row in report["current"]:
        assert row["rule_score"] == official[row["vessel_id"]]["score"]
        assert row["rule_band"] == official[row["vessel_id"]]["band"]
        assert 0.0 <= row["shadow_score"] <= 100.0
    assert official["V001"]["band"] == "High"
    assert official["V004"]["band"] == "High"
