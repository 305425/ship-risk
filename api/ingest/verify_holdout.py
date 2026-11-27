"""Score the held-out sixth inspection with the registered model.

Those inspections are not in the training upload. The features use only the
earlier rounds.
"""

import json
import os
from pathlib import Path

import pandas as pd

from app.config import API_DIR
from app.model_registry import load_latest
from app.risk_model import training_frame
from app.schemas import TABLE_SPECS
from app.scoring import load_rules

ROOT = Path(__file__).resolve().parents[2]
TRAIN = ROOT / "data" / "train"
VERIFY = ROOT / "data" / "verify"


def _load(directory: Path, names: list[str] | None = None) -> dict[str, pd.DataFrame]:
    frames = {}
    for spec in TABLE_SPECS.values():
        path = directory / f"{spec.file_stem}.csv"
        if names is not None and spec.file_stem not in names:
            continue
        if not path.exists():
            continue
        raw = pd.read_csv(path, dtype=str, keep_default_na=False)
        frames[spec.table] = pd.DataFrame([spec.model(**row).model_dump() for row in raw.to_dict("records")])
    return frames


def main() -> None:
    os.environ["MLFLOW_DIR"] = str(API_DIR / "mlflow")
    loaded = load_latest()
    if loaded is None:
        raise SystemExit("No registered model")
    model, evaluation, registry = loaded
    data = _load(TRAIN)
    held = _load(VERIFY, ["Inspections", "Deficiencies", "Detentions"])
    for table, frame in held.items():
        data[table] = pd.concat([data[table], frame], ignore_index=True)
    manifest = json.loads((VERIFY / "manifest.json").read_text(encoding="utf-8"))
    held_ids = {item["inspection_id"] for item in manifest}
    frame = training_frame(data, load_rules(API_DIR / "rules.yaml"))
    holdout = frame[frame.inspection_id.isin(held_ids)].copy()
    columns = evaluation["features"]
    holdout["probability"] = model.predict_proba(holdout[columns].to_numpy(dtype=float))[:, 1]
    holdout = holdout.sort_values(["probability", "vessel_id"], ascending=[False, True])
    holdout["rank"] = range(1, len(holdout) + 1)
    by_id = {item["inspection_id"]: item for item in manifest}
    bad = holdout[holdout.label == 1]
    caught_10 = int((bad["rank"] <= 10).sum())
    caught_20 = int((bad["rank"] <= 20).sum())
    profiles = []
    for profile in ("chronic", "emerging", "recovered", "clean"):
        ids = {item["inspection_id"] for item in manifest if item["profile"] == profile}
        rows = holdout[holdout.inspection_id.isin(ids)]
        profiles.append({
            "profile": profile,
            "vessels": int(len(rows)),
            "bad": int(rows.label.sum()),
            "mean_rank": round(float(rows["rank"].mean()), 1),
            "mean_probability": round(float(rows.probability.mean()), 3),
        })
    print(json.dumps({
        "registry_version": registry["version"],
        "trigger": registry["trigger"],
        "training_rows": evaluation["rows"],
        "training_positives": evaluation["positives"],
        "forward_recall_at_3": evaluation["forward"]["recall_at_3"],
        "holdout_inspections": int(len(holdout)),
        "holdout_bad": int(bad.shape[0]),
        "recall_at_10": {"caught": caught_10, "bad": int(bad.shape[0])},
        "recall_at_20": {"caught": caught_20, "bad": int(bad.shape[0])},
        "profiles": profiles,
    }, indent=2))


if __name__ == "__main__":
    main()
