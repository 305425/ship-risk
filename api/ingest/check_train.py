"""Confirm the generated training CSVs validate and can train both classes."""

from pathlib import Path

import pandas as pd

from app.config import API_DIR
from app.risk_model import training_frame
from app.schemas import TABLE_SPECS
from app.scoring import load_rules
from app.upload import parse_file

ROOT = Path(__file__).resolve().parents[2] / "data" / "train"


def main() -> None:
    errors = []
    batch = {}
    for spec in TABLE_SPECS.values():
        path = ROOT / f"{spec.file_stem}.csv"
        parsed = parse_file(path.name, path.read_bytes())
        errors.extend(f"{e.file}:{e.row}:{e.column}:{e.message}" for e in parsed.errors)
        batch[spec.table] = parsed
    vessels = {row["vessel_id"] for row in batch["vessels"].rows}
    inspections = {row["inspection_id"]: row for row in batch["inspections"].rows}
    for table in ("deficiencies", "detentions", "crew", "maintenance", "audit_findings", "equipment_failures"):
        for row in batch[table].rows:
            if row["vessel_id"] not in vessels:
                errors.append(f"{table} unknown vessel {row['vessel_id']}")
            if table in ("deficiencies", "detentions"):
                inspection = inspections.get(row["inspection_id"])
                if inspection is None or inspection["vessel_id"] != row["vessel_id"]:
                    errors.append(f"{table} bad inspection {row['inspection_id']}")
    if errors:
        raise SystemExit("\n".join(errors[:12]))
    data = {}
    for spec in TABLE_SPECS.values():
        frame = pd.read_csv(ROOT / f"{spec.file_stem}.csv", dtype=str, keep_default_na=False)
        data[spec.table] = pd.DataFrame([spec.model(**row).model_dump() for row in frame.to_dict("records")])
    trained = training_frame(data, load_rules(API_DIR / "rules.yaml"))
    print(f"training_rows {len(trained)} positives {int(trained['label'].sum())}")


if __name__ == "__main__":
    main()
