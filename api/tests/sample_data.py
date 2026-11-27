from pathlib import Path

import pandas as pd

from app.schemas import TABLE_SPECS

DATA_DIR = Path(__file__).resolve().parents[2] / "data"


def load_sample() -> dict[str, pd.DataFrame]:
    out = {}
    for spec in TABLE_SPECS.values():
        frame = pd.read_csv(DATA_DIR / f"{spec.file_stem}.csv", dtype=str, keep_default_na=False)
        out[spec.table] = pd.DataFrame([spec.model(**r).model_dump() for r in frame.to_dict("records")])
    return out
