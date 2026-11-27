import os
from datetime import date

import pytest

from app.model_registry import publish, serve, store_dir
from app.risk_model import ShadowModelError

AS_OF = date(2026, 11, 25)


@pytest.fixture
def mlflow_home(tmp_path, monkeypatch):
    monkeypatch.setenv("MLFLOW_DIR", str(tmp_path))
    return tmp_path


def test_publish_writes_a_pickle_and_serve_loads_it(sample, rules, mlflow_home):
    first = publish(sample, rules, AS_OF, "upload", "batch-1")
    assert first["registry"]["version"] == "1"
    assert first["registry"]["trigger_ref"] == "batch-1"
    assert [row["vessel_id"] for row in first["current"][:2]] == ["V001", "V004"]
    assert any(path.name == "model.pkl" for path in mlflow_home.rglob("model.pkl"))

    second = publish(sample, rules, AS_OF, "upload", "batch-2")
    assert second["registry"]["version"] == "2"
    served = serve(sample, rules, AS_OF)
    assert served["registry"]["version"] == "2"
    assert served["registry"]["run_id"] == second["registry"]["run_id"]
    assert served["current"][0]["vessel_id"] == "V001"
    assert (store_dir() / "mlflow.db").is_file()


def test_failed_retrain_keeps_the_registered_version(sample, rules, mlflow_home):
    publish(sample, rules, AS_OF, "upload", "batch-1")
    broken = {**sample, "inspections": sample["inspections"].assign(inspection_result="No Major Findings")}
    with pytest.raises(ShadowModelError):
        publish(broken, rules, AS_OF, "upload", "batch-2")
    assert serve(sample, rules, AS_OF)["registry"]["version"] == "1"
    assert os.environ["MLFLOW_DIR"] == str(mlflow_home)
