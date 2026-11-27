"""Shadow logistic regression on the same raw features the rules already compute.

The rule score remains the number the dashboard and the chat quote. This model
only ranks which vessels, before an inspection, looked like the ones that then
had a major finding or a detention. It does not set the band, the overrides or
the actions.

Training rows use inspection and deficiency history dated strictly before the
inspection being predicted. Maintenance, crew, audit and equipment-failure
records are left out: in this sample they are dated after the inspections, so
they cannot be placed before the outcome.
"""

from datetime import date

import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .backtest import BACKTEST_COMPONENTS, _rules_for_backtest, _state_before
from .scoring import empty_data, prepare, score_fleet, vessel_facts

FEATURE_LABELS = {
    "inspection.last_result": "Last inspection result",
    "inspection.deficiency_trend": "Deficiency trend",
    "inspection.prior_bad_outcomes": "Prior major findings or detention",
    "deficiencies.open_severity": "Open deficiency severity",
    "deficiencies.open_age": "Age of open deficiencies",
    "deficiencies.recurring": "Recurring deficiencies",
}

CAVEATS = [
    "This is a shadow score. The fleet ranking, bands, overrides and actions still come from the rules.",
    "The model is a logistic regression with balanced class weights. The probability ranks vessels; it is not a calibrated chance of detention.",
    "Bad outcomes are a small share of the inspections. A result that looks strong in-sample can still be the model remembering those ships.",
    "Features are the raw inspection and deficiency values the rules already compute, taken only from records dated before the inspection being predicted.",
    "Maintenance, crew, audit and equipment-failure records are excluded because they are dated after the inspections.",
    "Round 1 is skipped because no vessel has any history before its first inspection.",
    "The forward check trains on earlier rounds and ranks the last round only. The leave-one-vessel-out check trains without the held-out ship, then ranks that ship against the others.",
    "The current shadow score stretches the model's log-odds across this fleet, from 0 for the lowest margin to 100 for the highest. Vessels can share a high probability and still have different scores.",
]


class ShadowModelError(ValueError):
    """The uploaded history cannot train a two-class model."""


def feature_columns(rules: dict) -> list[str]:
    return [
        f"{component}.{name}"
        for component in BACKTEST_COMPONENTS
        for name in rules["components"][component]["features"]
    ]


def training_frame(data: dict[str, pd.DataFrame], rules: dict) -> pd.DataFrame:
    """One row per vessel per inspection from round 2 on. The label is that inspection's own outcome."""
    prepared = prepare(data)
    point_rules = _rules_for_backtest(rules)
    columns = feature_columns(rules)
    bad = set(rules["bad_outcomes"])
    inspections = prepared["inspections"].sort_values(["vessel_id", "inspection_date"]).copy()
    inspections["round"] = inspections.groupby("vessel_id").cumcount() + 1

    rows = []
    for record in inspections.to_dict("records"):
        if int(record["round"]) < 2:
            continue
        cutoff = pd.Timestamp(record["inspection_date"])
        state = _state_before(prepared, record["vessel_id"], cutoff)
        frames = empty_data()
        for table, frame in state.items():
            frames[table] = frame
        facts = vessel_facts(record["vessel_id"], prepare(frames), point_rules, cutoff.date())
        row = {
            "vessel_id": record["vessel_id"],
            "inspection_id": record["inspection_id"],
            "inspection_date": cutoff.date().isoformat(),
            "round": int(record["round"]),
            "outcome": record["inspection_result"],
            "label": int(record["inspection_result"] in bad),
        }
        for component, features in facts.features.items():
            for name, feature in features.items():
                row[f"{component}.{name}"] = float(feature.value)
        rows.append(row)

    frame = pd.DataFrame(rows)
    missing = [name for name in columns if name not in frame.columns]
    if missing:
        raise ShadowModelError(f"training rows are missing features: {missing}")
    return frame


def _fit(features: pd.DataFrame, labels: pd.Series):
    model = make_pipeline(
        StandardScaler(),
        LogisticRegression(C=1.0, class_weight="balanced", solver="lbfgs", max_iter=2000, random_state=0),
    )
    model.fit(features.to_numpy(dtype=float), labels.to_numpy(dtype=int))
    return model


def _with_ranks(frame: pd.DataFrame, column: str) -> pd.DataFrame:
    out = frame.copy()
    out["rank"] = 0
    for index in out.groupby("round").groups.values():
        probabilities = out.loc[index, column].to_numpy()
        out.loc[index, "rank"] = [1 + int((probabilities > probability).sum()) for probability in probabilities]
    return out


def _outcome(row) -> dict:
    return {
        "vessel_id": row.vessel_id,
        "inspection_id": row.inspection_id,
        "round": int(row.round),
        "outcome": row.outcome,
        "probability": round(float(row.probability), 4),
        "rank": int(row.rank),
    }


def _bad_outcomes(frame: pd.DataFrame) -> list[dict]:
    bad = frame[frame["label"] == 1].sort_values(["round", "vessel_id"])
    return [_outcome(row) for row in bad.itertuples(index=False)]


def _recall(outcomes: list[dict], top_n: int) -> dict:
    caught = sum(item["rank"] <= top_n for item in outcomes)
    return {
        "top_n": top_n,
        "bad_outcomes": len(outcomes),
        "caught": caught,
        "recall": round(caught / len(outcomes), 3) if outcomes else None,
    }


def _coefficients(model, columns: list[str]) -> list[dict]:
    weights = model.named_steps["logisticregression"].coef_.ravel()
    order = sorted(range(len(columns)), key=lambda i: -abs(float(weights[i])))
    return [
        {
            "feature": columns[i],
            "label": FEATURE_LABELS.get(columns[i], columns[i]),
            "coefficient": round(float(weights[i]), 4),
        }
        for i in order
    ]


def _can_train(labels: pd.Series) -> bool:
    return labels.nunique() >= 2 and len(labels) >= 2


def fit_and_evaluate(frame: pd.DataFrame, columns: list[str]) -> tuple:
    """Fit the served model and the checks. The checks are stored with the MLflow run."""
    if not _can_train(frame["label"]):
        raise ShadowModelError("Need at least one bad outcome and one routine inspection with prior history to train")

    model = _fit(frame[columns], frame["label"])
    fitted = _with_ranks(frame.assign(probability=model.predict_proba(frame[columns].to_numpy(dtype=float))[:, 1]), "probability")
    in_sample = _bad_outcomes(fitted)

    last_round = int(frame["round"].max())
    earlier = frame["round"] < last_round
    forward_outcomes: list[dict] = []
    forward_note = None
    if _can_train(frame.loc[earlier, "label"]):
        forward_model = _fit(frame.loc[earlier, columns], frame.loc[earlier, "label"])
        held_round = frame.loc[~earlier].copy()
        held_round["probability"] = forward_model.predict_proba(held_round[columns].to_numpy(dtype=float))[:, 1]
        forward_outcomes = _bad_outcomes(_with_ranks(held_round, "probability"))
    else:
        forward_note = f"Round {last_round} was not ranked: the earlier rounds do not contain both classes."

    loo_outcomes: list[dict] = []
    skipped: list[str] = []
    for vessel in sorted(frame.loc[frame["label"] == 1, "vessel_id"].unique()):
        train = frame["vessel_id"] != vessel
        if not _can_train(frame.loc[train, "label"]):
            skipped.append(vessel)
            continue
        held_model = _fit(frame.loc[train, columns], frame.loc[train, "label"])
        scored = frame.copy()
        scored["probability"] = held_model.predict_proba(scored[columns].to_numpy(dtype=float))[:, 1]
        ranked = _with_ranks(scored, "probability")
        loo_outcomes.extend(_bad_outcomes(ranked[(ranked["vessel_id"] == vessel) & (ranked["label"] == 1)]))

    caveats = list(CAVEATS)
    if forward_note:
        caveats.append(forward_note)
    if skipped:
        caveats.append(
            "Leave-one-vessel-out skipped "
            + ", ".join(skipped)
            + " because holding that vessel out left only one class."
        )

    evaluation = {
        "model": "logistic_regression",
        "role": "shadow",
        "features": columns,
        "rows": int(len(frame)),
        "positives": int(frame["label"].sum()),
        "coefficients": _coefficients(model, columns),
        "intercept": round(float(model.named_steps["logisticregression"].intercept_[0]), 4),
        "in_sample": {"bad_outcomes": in_sample, "recall_at_2": _recall(in_sample, 2), "recall_at_3": _recall(in_sample, 3)},
        "forward": {
            "trained_on_rounds_before": last_round,
            "bad_outcomes": forward_outcomes,
            "recall_at_2": _recall(forward_outcomes, 2),
            "recall_at_3": _recall(forward_outcomes, 3),
        },
        "leave_one_vessel_out": {
            "bad_outcomes": loo_outcomes,
            "recall_at_2": _recall(loo_outcomes, 2),
            "recall_at_3": _recall(loo_outcomes, 3),
        },
        "caveats": caveats,
    }
    return model, evaluation


def score_current(model, data: dict[str, pd.DataFrame], rules: dict, as_of: date, columns: list[str]) -> list[dict]:
    """Rank the fleet with a fitted model. Rule scores are copied through and not changed."""
    official = {row["vessel_id"]: row for row in score_fleet(data, rules, as_of)}
    current_frame = _current_features(data, rules, as_of, columns)
    matrix = current_frame[columns].to_numpy(dtype=float)
    current_frame["probability"] = model.predict_proba(matrix)[:, 1]
    current_frame["margin"] = model.decision_function(matrix)
    current_frame = current_frame.sort_values(["margin", "vessel_id"], ascending=[False, True])
    margins = current_frame["margin"].to_numpy(dtype=float)
    low, high = float(margins.min()), float(margins.max())
    span = high - low
    current = []
    for row in current_frame.itertuples(index=False):
        rule = official[row.vessel_id]
        margin = float(row.margin)
        current.append({
            "rank": 1 + int((margins > margin).sum()),
            "vessel_id": row.vessel_id,
            "vessel_name": row.vessel_name,
            "probability": round(float(row.probability), 4),
            "margin": round(margin, 4),
            "shadow_score": round(0.0 if span == 0 else 100 * (margin - low) / span, 1),
            "rule_score": rule["score"],
            "rule_band": rule["band"],
        })
    return current


def shadow_report(data: dict[str, pd.DataFrame], rules: dict, as_of: date) -> dict:
    """Train in memory and score. The API serves the MLflow-registered model instead."""
    frame = training_frame(data, rules)
    model, evaluation = fit_and_evaluate(frame, feature_columns(rules))
    return {**evaluation, "current": score_current(model, data, rules, as_of, evaluation["features"])}


def _current_features(data: dict[str, pd.DataFrame], rules: dict, as_of: date, columns: list[str]) -> pd.DataFrame:
    prepared = prepare(data)
    point_rules = _rules_for_backtest(rules)
    rows = []
    for vessel in prepared["vessels"].sort_values("vessel_id").to_dict("records"):
        facts = vessel_facts(vessel["vessel_id"], prepared, point_rules, as_of)
        row = {"vessel_id": vessel["vessel_id"], "vessel_name": vessel["vessel_name"]}
        for component, features in facts.features.items():
            for name, feature in features.items():
                row[f"{component}.{name}"] = float(feature.value)
        rows.append(row)
    frame = pd.DataFrame(rows)
    missing = [name for name in columns if name not in frame.columns]
    if missing:
        raise ShadowModelError(f"current rows are missing features: {missing}")
    return frame
