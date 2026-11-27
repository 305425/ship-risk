import pandas as pd
import pytest

from app.backtest import _state_before, run_backtest
from app.scoring import prepare


@pytest.fixture(scope="module")
def result(sample, rules):
    return run_backtest(sample, rules, top_n=2)


def test_rounds_skip_first_inspection(result):
    assert [r["round"] for r in result["rounds"]] == [2, 3, 4]
    assert all(len(r["ranking"]) == 20 for r in result["rounds"])


def test_bad_outcome_ranks(result):
    ranks = {(o["inspection_id"], o["outcome"]): o["rank"] for o in result["bad_outcomes"]}
    assert ranks == {
        ("INS0003", "Major Deficiencies"): 1,
        ("INS0004", "Detained"): 1,
        ("INS0016", "Detained"): 3,
    }


def test_recall_curve(result):
    recall = {c["top_n"]: c["recall"] for c in result["recall_curve"]}
    assert recall[2] == pytest.approx(2 / 3, abs=1e-3)
    assert recall[3] == 1.0
    assert result["summary"]["top_n"] == 2


def test_state_before_uses_only_earlier_records(sample):
    d = prepare(sample)
    cutoff = pd.Timestamp("2025-06-29")  # V001's detention inspection
    state = _state_before(d, "V001", cutoff)
    assert list(state["inspections"].inspection_id) == ["INS0001", "INS0002", "INS0003"]
    assert state["detentions"].empty
    assert (state["inspections"].inspection_date < cutoff).all()
    closed = state["deficiencies"][state["deficiencies"].deficiency_status == "Closed"]
    assert (closed.deficiency_closed_date < cutoff).all()


def test_deficiencies_closed_after_cutoff_count_as_open(sample):
    d = prepare(sample)
    defs = d["deficiencies"]
    row = defs[(defs.vessel_id == "V001") & (defs.inspection_id == "INS0001")].iloc[0]
    cutoff = row.deficiency_closed_date  # closed on this day, so still open just before it
    state = _state_before(d, "V001", cutoff + pd.Timedelta(days=0))
    reopened = state["deficiencies"].set_index("deficiency_id").loc[row.deficiency_id]
    assert reopened.deficiency_status == "Open" and pd.isna(reopened.deficiency_closed_date)


def test_backtest_ignores_later_tables(sample, rules):
    without_late_tables = {k: v for k, v in sample.items()
                           if k not in ("maintenance", "crew", "audit_findings", "equipment_failures")}
    assert run_backtest(without_late_tables, rules) == run_backtest(sample, rules)
