"""Rule-based risk score: features per vessel, fleet normalisation, overrides, bands and confidence.

Pure functions over pandas DataFrames, so the same code serves the API, the tests and the backtest.
"""

from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path

import pandas as pd
import yaml

DATE_COLUMNS = {
    "inspections": ["inspection_date"],
    "deficiencies": ["deficiency_closed_date"],
    "detentions": ["detention_date"],
    "crew": ["join_date"],
    "equipment_failures": ["equipment_failure_date"],
    "maintenance": ["maintenance_due_date", "maintenance_completed_date"],
}

COLUMNS = {
    "vessels": ["vessel_id", "imo_number", "vessel_name", "vessel_type", "build_year", "flag_state"],
    "inspections": ["inspection_id", "vessel_id", "inspection_date", "inspection_port", "inspection_authority",
                    "inspection_type", "inspection_result", "detention_flag"],
    "deficiencies": ["deficiency_id", "inspection_id", "vessel_id", "deficiency_code", "deficiency_category",
                     "deficiency_description", "deficiency_status", "deficiency_closed_date"],
    "detentions": ["inspection_id", "vessel_id", "detention_date", "detention_reason"],
    "audit_findings": ["audit_id", "vessel_id", "audit_finding_description", "audit_finding_status"],
    "crew": ["crew_id", "vessel_id", "rank", "join_date", "rank_experience_months", "training_status", "stcw_status"],
    "equipment_failures": ["failure_id", "vessel_id", "equipment_name", "equipment_failure_date",
                           "equipment_failure_description"],
    "maintenance": ["maintenance_id", "vessel_id", "maintenance_equipment_name", "maintenance_due_date",
                    "maintenance_completed_date", "maintenance_status"],
}

RESOLVABLE = {
    "deficiencies": "deficiency_id",
    "maintenance": "maintenance_id",
    "audit_findings": "audit_id",
    "crew": "crew_id",
}

CONFIDENCE_ORDER = {"high": 0, "medium": 1, "low": 2}


@dataclass
class Feature:
    value: float
    detail: str
    record_ids: list[str] = field(default_factory=list)


@dataclass
class Trigger:
    type: str
    subject: str
    record_ids: list[str]
    category: str | None = None
    count: int = 0


@dataclass
class VesselFacts:
    features: dict[str, dict[str, Feature]]
    overrides: list[dict]
    triggers: list[Trigger]
    confidence_reasons: list[dict]


def load_rules(path: str | Path) -> dict:
    with open(path, encoding="utf-8") as fh:
        rules = yaml.safe_load(fh)
    for name, component in rules["components"].items():
        total = sum(component["features"].values())
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"rules.yaml: feature weights of component '{name}' sum to {total}, not 1")
        unknown = set(component["features"]) - set(FEATURE_FUNCTIONS[name])
        if unknown:
            raise ValueError(f"rules.yaml: unknown features in '{name}': {sorted(unknown)}")
    return rules


def empty_data() -> dict[str, pd.DataFrame]:
    return {t: pd.DataFrame(columns=c) for t, c in COLUMNS.items()}


def prepare(data: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    out = {}
    for table, columns in COLUMNS.items():
        frame = data.get(table)
        frame = pd.DataFrame(columns=columns) if frame is None else frame.copy()
        for column in DATE_COLUMNS.get(table, []):
            frame[column] = pd.to_datetime(frame[column], errors="coerce")
        out[table] = frame
    return out


def apply_resolutions(data: dict[str, pd.DataFrame], resolved: dict[str, set[str]], as_of: date) -> dict[str, pd.DataFrame]:
    """Treat records fixed by completed actions as resolved until a new upload of their table arrives."""
    out = dict(data)
    stamp = pd.Timestamp(as_of)
    for table, ids in resolved.items():
        if not ids or table not in RESOLVABLE:
            continue
        frame = data[table].copy()
        mask = frame[RESOLVABLE[table]].isin(ids)
        if table == "deficiencies":
            frame.loc[mask & (frame.deficiency_status == "Open"), "deficiency_closed_date"] = stamp
            frame.loc[mask, "deficiency_status"] = "Closed"
        elif table == "maintenance":
            frame.loc[mask & (frame.maintenance_status != "Completed"), "maintenance_completed_date"] = stamp
            frame.loc[mask, "maintenance_status"] = "Completed"
        elif table == "audit_findings":
            frame.loc[mask, "audit_finding_status"] = "Closed"
        elif table == "crew":
            frame.loc[mask, "training_status"] = "Compliant"
            frame.loc[mask, "stcw_status"] = "Valid"
        out[table] = frame
    return out


def _ids(frame: pd.DataFrame, column: str) -> list[str]:
    return sorted(frame[column].astype(str).tolist())


def _fmt_date(value) -> str:
    return pd.Timestamp(value).date().isoformat()


class _VesselView:
    """One vessel's rows from every table, with shared derived values."""

    def __init__(self, vessel_id: str, d: dict[str, pd.DataFrame], rules: dict, as_of: date):
        self.vessel_id = vessel_id
        self.rules = rules
        self.as_of = pd.Timestamp(as_of)
        pick = lambda t: d[t][d[t].vessel_id == vessel_id]
        self.inspections = pick("inspections").sort_values("inspection_date")
        dates = dict(zip(self.inspections.inspection_id, self.inspections.inspection_date))
        defs = pick("deficiencies").copy()
        defs["inspection_date"] = pd.to_datetime(defs.inspection_id.map(dates))
        self.deficiencies = defs
        self.detentions = pick("detentions")
        self.audits = pick("audit_findings")
        self.crew = pick("crew")
        self.failures = pick("equipment_failures")
        self.maintenance = pick("maintenance")
        self.last_inspection = self.inspections.iloc[-1] if len(self.inspections) else None
        self.open_defs = defs[defs.deficiency_status == "Open"].copy()
        if self.last_inspection is not None:
            self.open_defs["carried_days"] = (self.last_inspection.inspection_date - self.open_defs.inspection_date).dt.days
        else:
            self.open_defs["carried_days"] = 0
        self.overdue = self.maintenance[self.maintenance.maintenance_status == "Overdue"]
        self.senior = self.crew[self.crew["rank"].isin(rules["senior_ranks"])]


# --- Inspection history -------------------------------------------------------------------------------------

def _last_result(v: _VesselView) -> Feature:
    if v.last_inspection is None:
        return Feature(0.0, "No inspections on record")
    li = v.last_inspection
    value = v.rules["inspection_result_values"].get(li.inspection_result, 0.0)
    return Feature(value, f"Last inspection {li.inspection_id} ({_fmt_date(li.inspection_date)}): {li.inspection_result}",
                   [li.inspection_id])


def _deficiency_trend(v: _VesselView) -> Feature:
    if len(v.inspections) < 2:
        return Feature(0.0, "Not enough inspections for a trend")
    counts = v.deficiencies.groupby("inspection_id").size()
    series = [int(counts.get(i, 0)) for i in v.inspections.inspection_id]
    earlier = sum(series[:-1]) / len(series[:-1])
    value = max(0.0, series[-1] - earlier)
    return Feature(value, "Deficiencies per inspection: " + " → ".join(map(str, series)),
                   [v.last_inspection.inspection_id])


def _prior_bad_outcomes(v: _VesselView) -> Feature:
    bad = v.inspections[v.inspections.inspection_result.isin(v.rules["bad_outcomes"])]
    detail = ", ".join(f"{r.inspection_id} {r.inspection_result}" for r in bad.itertuples()) or "None"
    return Feature(float(len(bad)), f"Major deficiencies or detention: {detail}", _ids(bad, "inspection_id"))


# --- Deficiencies -------------------------------------------------------------------------------------------

def _open_severity(v: _VesselView) -> Feature:
    weights = v.rules["severity_weights"]
    value = float(v.open_defs.deficiency_category.map(weights).fillna(1).sum())
    by_cat = Counter(v.open_defs.deficiency_category)
    detail = ", ".join(f"{c} {n}" for c, n in by_cat.most_common())
    return Feature(value, f"{len(v.open_defs)} open deficiencies" + (f" ({detail})" if detail else ""),
                   _ids(v.open_defs, "deficiency_id"))


def _open_age(v: _VesselView) -> Feature:
    carried = v.open_defs[v.open_defs.carried_days > 0]
    if carried.empty:
        return Feature(0.0, "No open deficiencies carried past a later inspection")
    return Feature(float(carried.carried_days.sum()),
                   f"{len(carried)} open deficiencies still open at a later inspection, oldest {int(carried.carried_days.max())} days",
                   _ids(carried, "deficiency_id"))


def _recurrences(v: _VesselView, min_inspections: int) -> pd.Series:
    n = v.deficiencies.groupby("deficiency_description").inspection_id.nunique()
    return n[n >= min_inspections].sort_values(ascending=False)


def _recurring(v: _VesselView) -> Feature:
    rec = _recurrences(v, v.rules["thresholds"]["recurring_min_inspections"])
    if rec.empty:
        return Feature(0.0, "No recurring deficiencies")
    rows = v.deficiencies[v.deficiencies.deficiency_description.isin(rec.index)]
    detail = "; ".join(f"'{d}' at {n} inspections" for d, n in rec.head(3).items())
    return Feature(float(((rec - 1) ** 2).sum()), f"{len(rec)} recurring: {detail}", _ids(rows, "deficiency_id"))


# --- Maintenance & equipment --------------------------------------------------------------------------------

def _pct_overdue(v: _VesselView) -> Feature:
    total = len(v.maintenance)
    if total == 0:
        return Feature(0.0, "No maintenance records")
    n = len(v.overdue)
    return Feature(n / total, f"{n / total:.0%} of maintenance overdue ({n} of {total})", _ids(v.overdue, "maintenance_id"))


def _overdue_critical(v: _VesselView) -> Feature:
    crit = v.overdue[v.overdue.maintenance_equipment_name.isin(v.rules["critical_equipment"])]
    by_item = Counter(crit.maintenance_equipment_name)
    detail = ", ".join(f"{e} {n}" for e, n in by_item.most_common())
    return Feature(float(len(crit)), f"{len(crit)} overdue jobs on critical equipment" + (f" ({detail})" if detail else ""),
                   _ids(crit, "maintenance_id"))


def _repeat_failures(v: _VesselView) -> Feature:
    counts = v.failures.groupby("equipment_name").size()
    repeat = counts[counts >= v.rules["thresholds"]["repeat_failure_count"]].sort_values(ascending=False)
    if repeat.empty:
        return Feature(0.0, "No repeat equipment failures")
    rows = v.failures[v.failures.equipment_name.isin(repeat.index)]
    detail = ", ".join(f"{e} failed {n} times" for e, n in repeat.items())
    return Feature(float(repeat.sum()), f"Repeat failures: {detail}", _ids(rows, "failure_id"))


# --- Crew ---------------------------------------------------------------------------------------------------

def _recent_senior_joiners(v: _VesselView) -> Feature:
    days = v.rules["thresholds"]["recent_joiner_days"]
    recent = v.senior[v.senior.join_date >= v.as_of - pd.Timedelta(days=days)]
    detail = ", ".join(sorted(recent["rank"]))
    return Feature(float(len(recent)), f"{len(recent)} senior officers joined in the last {days} days"
                   + (f" ({detail})" if detail else ""), _ids(recent, "crew_id"))


def _low_rank_experience(v: _VesselView) -> Feature:
    months = v.rules["thresholds"]["low_rank_experience_months"]
    low = v.senior[v.senior.rank_experience_months.astype(int) < months]
    detail = ", ".join(f"{r.rank} {r.rank_experience_months} months" for r in low.itertuples())
    return Feature(float(len(low)), f"{len(low)} senior officers under {months} months in rank"
                   + (f" ({detail})" if detail else ""), _ids(low, "crew_id"))


def _training_pending(v: _VesselView) -> Feature:
    pending = v.crew[v.crew.training_status == "Pending"]
    detail = ", ".join(sorted(pending["rank"]))
    return Feature(float(len(pending)), f"{len(pending)} crew with training pending" + (f" ({detail})" if detail else ""),
                   _ids(pending, "crew_id"))


def _stcw_expiring(v: _VesselView) -> Feature:
    bad = v.crew[v.crew.stcw_status != "Valid"]
    detail = ", ".join(f"{r.rank} {r.stcw_status}" for r in bad.itertuples())
    return Feature(float(len(bad)), f"{len(bad)} crew with STCW expiring or expired" + (f" ({detail})" if detail else ""),
                   _ids(bad, "crew_id"))


# --- Audit / ISM --------------------------------------------------------------------------------------------

def _overdue_findings(v: _VesselView) -> Feature:
    overdue = v.audits[v.audits.audit_finding_status == "Overdue"]
    return Feature(float(len(overdue)), f"{len(overdue)} overdue audit findings", _ids(overdue, "audit_id"))


def _repeats_deficiency(v: _VesselView) -> Feature:
    known = set(v.deficiencies.deficiency_description)
    unresolved = v.audits[v.audits.audit_finding_status != "Closed"]
    repeats = unresolved[unresolved.audit_finding_description.isin(known)]
    detail = "; ".join(sorted(set(repeats.audit_finding_description))[:3])
    return Feature(float(len(repeats)), f"{len(repeats)} unresolved audit findings repeat an inspection deficiency"
                   + (f" ({detail})" if detail else ""), _ids(repeats, "audit_id"))


FEATURE_FUNCTIONS = {
    "inspection": {"last_result": _last_result, "deficiency_trend": _deficiency_trend,
                   "prior_bad_outcomes": _prior_bad_outcomes},
    "deficiencies": {"open_severity": _open_severity, "open_age": _open_age, "recurring": _recurring},
    "maintenance": {"pct_overdue": _pct_overdue, "overdue_critical": _overdue_critical,
                    "repeat_failures": _repeat_failures},
    "crew": {"recent_senior_joiners": _recent_senior_joiners, "low_rank_experience": _low_rank_experience,
             "training_pending": _training_pending, "stcw_expiring": _stcw_expiring},
    "audit": {"overdue_findings": _overdue_findings, "repeats_deficiency": _repeats_deficiency},
}


# --- Overrides, triggers, confidence ------------------------------------------------------------------------

def _overrides_and_triggers(v: _VesselView) -> tuple[list[dict], list[Trigger]]:
    cfg = v.rules["overrides"]
    overrides: list[dict] = []
    triggers: list[Trigger] = []

    def add(kind: str, text: str, subject: str, ids: list[str], category: str | None = None) -> None:
        overrides.append({"id": kind, "text": text, "record_ids": ids})
        triggers.append(Trigger(kind, subject, ids, category, len(ids)))

    c = cfg["recent_detention"]
    since = v.as_of - pd.DateOffset(months=c["months"])
    recent = v.detentions[v.detentions.detention_date >= since]
    if not recent.empty:
        add("recent_detention", c["text"].format(months=c["months"]), "detention", _ids(recent, "inspection_id"))

    c = cfg["aged_open_deficiency"]
    aged = v.open_defs[v.open_defs.deficiency_category.isin(c["categories"]) & (v.open_defs.carried_days >= c["days"])]
    for category, rows in aged.groupby("deficiency_category"):
        add("aged_open_deficiency", c["text"].format(category=category, days=c["days"]), category,
            _ids(rows, "deficiency_id"), category)

    c = cfg["senior_certification"]
    flagged = v.crew[v.crew["rank"].isin(c["ranks"]) & ((v.crew.training_status != "Compliant") | (v.crew.stcw_status != "Valid"))]
    if not flagged.empty:
        ranks = ", ".join(sorted(set(flagged["rank"])))
        add("senior_certification", c["text"].format(rank=ranks), "certification", _ids(flagged, "crew_id"))

    c = cfg["critical_overdue_cluster"]
    failures = v.failures.groupby("equipment_name").size()
    crit = v.overdue[v.overdue.maintenance_equipment_name.isin(v.rules["critical_equipment"])]
    for equipment, rows in crit.groupby("maintenance_equipment_name"):
        n_fail = int(failures.get(equipment, 0))
        if len(rows) >= c["min_overdue"] and n_fail >= c["min_failures"]:
            add("critical_overdue_cluster",
                c["text"].format(min_overdue=c["min_overdue"], equipment=equipment, failures=n_fail),
                equipment, _ids(rows, "maintenance_id"))

    strong = _recurrences(v, v.rules["thresholds"]["recurring_strong_inspections"])
    for description in strong.index:
        rows = v.deficiencies[v.deficiencies.deficiency_description == description].sort_values("inspection_date")
        open_rows = rows[rows.deficiency_status == "Open"]
        triggers.append(Trigger("recurring_deficiency", description, _ids(open_rows if len(open_rows) else rows, "deficiency_id"),
                                rows.iloc[-1].deficiency_category, int(strong[description])))

    overdue_audits = v.audits[v.audits.audit_finding_status == "Overdue"]
    if not overdue_audits.empty:
        triggers.append(Trigger("overdue_audit_findings", "audit", _ids(overdue_audits, "audit_id"),
                                count=len(overdue_audits)))
    return overrides, triggers


def _confidence_reasons(v: _VesselView) -> list[dict]:
    cfg = v.rules["confidence"]
    reasons = []
    if v.last_inspection is not None:
        age = (v.as_of - v.last_inspection.inspection_date).days / 30.44
        if age > cfg["max_inspection_age_months"]:
            reasons.append({"check": "stale_inspection",
                            "text": f"Last inspection {_fmt_date(v.last_inspection.inspection_date)} is {age:.0f} months old"})
    for name, frame in (("inspections", v.inspections), ("crew", v.crew), ("maintenance", v.maintenance)):
        if frame.empty:
            reasons.append({"check": "missing_source", "text": f"No {name} records for this vessel"})
    stale_open = v.maintenance[(v.maintenance.maintenance_status == "Open") & (v.maintenance.maintenance_due_date < v.as_of)]
    future_done = v.maintenance[v.maintenance.maintenance_completed_date > v.as_of]
    if len(stale_open):
        reasons.append({"check": "stale_records",
                        "text": f"{len(stale_open)} maintenance jobs marked Open are past their due date"})
    if len(future_done):
        reasons.append({"check": "stale_records",
                        "text": f"{len(future_done)} maintenance jobs have a completion date in the future"})
    for r in reasons:
        r["level"] = cfg["checks"][r["check"]]
    return reasons


def vessel_facts(vessel_id: str, d: dict[str, pd.DataFrame], rules: dict, as_of: date) -> VesselFacts:
    v = _VesselView(vessel_id, d, rules, as_of)
    features = {
        comp: {name: FEATURE_FUNCTIONS[comp][name](v) for name in cfg["features"]}
        for comp, cfg in rules["components"].items()
    }
    overrides, triggers = _overrides_and_triggers(v)
    return VesselFacts(features, overrides, triggers, _confidence_reasons(v))


def _band(score: float, overridden: bool, bands: dict) -> str:
    if overridden or score >= bands["high"]:
        return "High"
    return "Medium" if score >= bands["medium"] else "Low"


def score_fleet(
    data: dict[str, pd.DataFrame],
    rules: dict,
    as_of: date,
    resolved: dict[str, set[str]] | None = None,
) -> list[dict]:
    """Score every vessel. Normalisation uses the uploaded data, so resolving one vessel's records never moves another's score."""
    raw = prepare(data)
    effective = prepare(apply_resolutions(raw, resolved, as_of)) if resolved else raw
    vessels = raw["vessels"].sort_values("vessel_id")
    ids = vessels.vessel_id.tolist()

    raw_facts = {vid: vessel_facts(vid, raw, rules, as_of) for vid in ids}
    facts = {vid: vessel_facts(vid, effective, rules, as_of) for vid in ids} if resolved else raw_facts
    percentile = rules["normalization"]["percentile"]

    def reference(values: list[float]) -> float:
        if not values:
            return 0.0
        ref = float(pd.Series(values).quantile(percentile))
        return ref if ref > 0 else max(values)

    maxima = {
        comp: {name: reference([raw_facts[vid].features[comp][name].value for vid in ids]) for name in cfg["features"]}
        for comp, cfg in rules["components"].items()
    }

    results = []
    for vessel in vessels.itertuples():
        f = facts[vessel.vessel_id]
        components, contributions = {}, []
        for comp, cfg in rules["components"].items():
            feats, points_total = {}, 0.0
            for name, weight in cfg["features"].items():
                feature = f.features[comp][name]
                top = maxima[comp][name]
                normalized = min(1.0, feature.value / top) if top > 0 else 0.0
                points = cfg["max_points"] * weight * normalized
                points_total += points
                feats[name] = {**asdict(feature), "normalized": round(normalized, 4), "points": round(points, 2)}
                if points > 0:
                    contributions.append({"component": comp, "feature": name, "owner": cfg["owner"],
                                          "text": feature.detail, "points": round(points, 2),
                                          "record_ids": feature.record_ids})
            components[comp] = {"label": cfg["label"], "owner": cfg["owner"], "max_points": cfg["max_points"],
                                "points": round(points_total, 2), "features": feats}

        score = round(sum(c["points"] for c in components.values()), 1)
        level = max((r["level"] for r in f.confidence_reasons), key=CONFIDENCE_ORDER.get, default="high")
        results.append({
            "vessel_id": vessel.vessel_id,
            "vessel_name": vessel.vessel_name,
            "imo_number": str(vessel.imo_number),
            "score": score,
            "band": _band(score, bool(f.overrides), rules["bands"]),
            "confidence": level.capitalize(),
            "confidence_reasons": f.confidence_reasons,
            "components": components,
            "overrides": f.overrides,
            "drivers": sorted(contributions, key=lambda c: -c["points"])[:3],
            "triggers": [asdict(t) for t in f.triggers],
        })
    return results
