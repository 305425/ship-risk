"""Point-in-time backtest: score each vessel using only data dated before its inspection, then rank per round.

Only the inspection and deficiency components are used: maintenance, crew, audit and failure records in the
sample data are dated after the inspections, so they can't be placed in time.
"""

import copy

import pandas as pd

from .scoring import COLUMNS, prepare, score_fleet

BACKTEST_COMPONENTS = ("inspection", "deficiencies")

CAVEATS = [
    "Only 3 bad outcomes (V001 Major Deficiencies and Detention, V004 Detention) to test against: "
    "encouraging, not proof.",
    "The weights and thresholds were set after seeing this data, so the result is at risk of overfitting.",
    "Only inspection and deficiency history is backtested; maintenance, crew, audit and failure records are "
    "dated after the inspections.",
    "Round 1 is skipped because no vessel has any history before its first inspection.",
    "Vessels with equal scores share a rank and are all flagged at the cut-off, so a round with many ties "
    "(round 2, where every vessel has one prior inspection) raises the flag count.",
]


def _rules_for_backtest(rules: dict) -> dict:
    bt = copy.deepcopy(rules)
    bt["components"] = {name: rules["components"][name] for name in BACKTEST_COMPONENTS}
    return bt


def _state_before(d: dict[str, pd.DataFrame], vessel_id: str, cutoff: pd.Timestamp) -> dict[str, pd.DataFrame]:
    """One vessel's inspection, deficiency and detention records as they stood just before `cutoff`."""
    ins = d["inspections"]
    ins = ins[(ins.vessel_id == vessel_id) & (ins.inspection_date < cutoff)]
    defs = d["deficiencies"]
    defs = defs[defs.inspection_id.isin(ins.inspection_id)].copy()
    closed_later = defs.deficiency_closed_date.isna() | (defs.deficiency_closed_date >= cutoff)
    defs.loc[closed_later, "deficiency_status"] = "Open"
    defs.loc[closed_later, "deficiency_closed_date"] = pd.NaT
    det = d["detentions"]
    det = det[(det.vessel_id == vessel_id) & (det.detention_date < cutoff)]
    return {"inspections": ins, "deficiencies": defs, "detentions": det}


def run_backtest(data: dict[str, pd.DataFrame], rules: dict, top_n: int = 2) -> dict:
    d = prepare(data)
    bt_rules = _rules_for_backtest(rules)
    bad = set(rules["bad_outcomes"])
    ins = d["inspections"].sort_values(["vessel_id", "inspection_date"]).copy()
    ins["round"] = ins.groupby("vessel_id").cumcount() + 1

    rounds, outcomes = [], []
    for rnd in sorted(ins["round"].unique()):
        if rnd < 2:
            continue
        targets = ins[ins["round"] == rnd]
        states = [_state_before(d, t.vessel_id, t.inspection_date) for t in targets.itertuples()]
        round_data = {t: pd.DataFrame(columns=c) for t, c in COLUMNS.items()}
        round_data["vessels"] = d["vessels"][d["vessels"].vessel_id.isin(targets.vessel_id)]
        for table in ("inspections", "deficiencies", "detentions"):
            parts = [s[table] for s in states if not s[table].empty]
            if parts:
                round_data[table] = pd.concat(parts, ignore_index=True)
        as_of = targets.inspection_date.max().date()
        scores = {r["vessel_id"]: r for r in score_fleet(round_data, bt_rules, as_of)}

        ranking = []
        for t in targets.itertuples():
            s = scores[t.vessel_id]
            ranking.append({
                "vessel_id": t.vessel_id,
                "inspection_id": t.inspection_id,
                "inspection_date": t.inspection_date.date().isoformat(),
                "score": s["score"],
                "outcome": t.inspection_result,
                "bad_outcome": t.inspection_result in bad,
                "top_driver": s["drivers"][0]["text"] if s["drivers"] else None,
            })
        for row in ranking:
            row["rank"] = 1 + sum(other["score"] > row["score"] for other in ranking)
            row["tied_with"] = sum(other["score"] == row["score"] for other in ranking) - 1
            row["flagged"] = row["rank"] <= top_n
        ranking.sort(key=lambda r: (r["rank"], r["vessel_id"]))

        flagged = [r for r in ranking if r["flagged"]]
        rounds.append({
            "round": int(rnd),
            "date_range": [targets.inspection_date.min().date().isoformat(), as_of.isoformat()],
            "flagged": len(flagged),
            "bad_outcomes": sum(r["bad_outcome"] for r in ranking),
            "bad_outcomes_flagged": sum(r["bad_outcome"] for r in flagged),
            "ranking": ranking,
        })
        outcomes += [{**{k: r[k] for k in ("vessel_id", "inspection_id", "inspection_date", "outcome", "score",
                                            "rank", "tied_with", "flagged")}, "round": int(rnd)}
                     for r in ranking if r["bad_outcome"]]

    return {
        "top_n": top_n,
        "components": list(BACKTEST_COMPONENTS),
        "summary": _shortlist_stats(rounds, outcomes, top_n),
        "recall_curve": [_shortlist_stats(rounds, outcomes, n) for n in range(1, 6)],
        "bad_outcomes": outcomes,
        "rounds": rounds,
        "caveats": CAVEATS,
    }


def _shortlist_stats(rounds: list[dict], outcomes: list[dict], n: int) -> dict:
    """Recall and precision when every vessel ranked n or better is flagged; ties at the cut-off are all flagged."""
    caught = sum(o["rank"] <= n for o in outcomes)
    flags = sum(r["rank"] <= n for rd in rounds for r in rd["ranking"])
    return {
        "top_n": n,
        "bad_outcomes": len(outcomes),
        "caught": caught,
        "recall": round(caught / len(outcomes), 3) if outcomes else None,
        "flags": flags,
        "precision": round(caught / flags, 3) if flags else None,
    }
