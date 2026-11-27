"""Local MLflow registry for the shadow logistic regression.

The tracking store is a sqlite file and the model pickle lives under its artifact
folder. A successful CSV upload registers the next version. Serving loads that
version. A failed retrain leaves the previous version in place.
"""

import json
import logging
import os
import threading
from datetime import date, datetime, timezone
from pathlib import Path

import mlflow
from mlflow import MlflowClient

from .config import API_DIR
from .risk_model import feature_columns, fit_and_evaluate, score_current, training_frame

EXPERIMENT = "ship-risk-shadow"
REGISTERED_NAME = "ship-risk-shadow"
_LOCK = threading.Lock()
log = logging.getLogger(__name__)


def store_dir() -> Path:
    raw = os.environ.get("MLFLOW_DIR", "").strip()
    path = Path(raw) if raw else API_DIR / "mlflow"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _tracking() -> MlflowClient:
    os.environ["MLFLOW_RECORD_ENV_VARS_IN_MODEL_LOGGING"] = "false"
    store = store_dir()
    db = (store / "mlflow.db").resolve().as_posix()
    artifacts = store / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    uri = "sqlite:///" + db
    # The sqlite store creates ./mlruns in the process directory before the experiment
    # artifact path exists. That directory is not writable, so open the store from the
    # artifact folder and then return to the API directory.
    previous = os.getcwd()
    os.chdir(store)
    try:
        mlflow.set_tracking_uri(uri)
        client = MlflowClient(tracking_uri=uri)
        if client.get_experiment_by_name(EXPERIMENT) is None:
            client.create_experiment(EXPERIMENT, artifact_location=artifacts.resolve().as_uri())
        mlflow.set_experiment(EXPERIMENT)
        return client
    finally:
        os.chdir(previous)


def _latest_version(client: MlflowClient):
    versions = client.search_model_versions(f"name='{REGISTERED_NAME}'")
    if not versions:
        return None
    return max(versions, key=lambda version: int(version.version))


def _registry_record(version) -> dict:
    return {
        "name": REGISTERED_NAME,
        "version": str(version.version),
        "run_id": version.run_id,
        "trained_at": version.tags.get("trained_at", ""),
        "trigger": version.tags.get("trigger", ""),
        "trigger_ref": version.tags.get("trigger_ref") or None,
        "model_uri": version.source,
    }


def load_latest() -> tuple | None:
    """Return the registered pipeline, its saved checks, and the version record."""
    with _LOCK:
        client = _tracking()
        version = _latest_version(client)
        if version is None:
            return None
        model = mlflow.sklearn.load_model(f"models:/{REGISTERED_NAME}/{version.version}")
        local = mlflow.artifacts.download_artifacts(run_id=version.run_id, artifact_path="evaluation.json")
    evaluation = json.loads(Path(local).read_text(encoding="utf-8"))
    return model, evaluation, _registry_record(version)


def publish(data: dict, rules: dict, as_of: date, trigger: str, trigger_ref: str | None) -> dict:
    """Fit, log one MLflow run, and register the next model version."""
    frame = training_frame(data, rules)
    columns = feature_columns(rules)
    model, evaluation = fit_and_evaluate(frame, columns)
    trained_at = datetime.now(timezone.utc).isoformat()
    with _LOCK:
        client = _tracking()
        with mlflow.start_run(run_name=trigger_ref or trigger) as run:
            mlflow.set_tags({"trigger": trigger, "trigger_ref": trigger_ref or "", "trained_at": trained_at})
            mlflow.log_params({
                "model": "logistic_regression",
                "trigger": trigger,
                "rows": evaluation["rows"],
                "positives": evaluation["positives"],
            })
            mlflow.log_metrics({
                "in_sample_recall_at_3": evaluation["in_sample"]["recall_at_3"]["recall"] or 0.0,
                "forward_recall_at_3": evaluation["forward"]["recall_at_3"]["recall"] or 0.0,
                "leave_one_vessel_out_recall_at_3": evaluation["leave_one_vessel_out"]["recall_at_3"]["recall"] or 0.0,
            })
            mlflow.log_dict(evaluation, "evaluation.json")
            mlflow.sklearn.log_model(
                model,
                "model",
                registered_model_name=REGISTERED_NAME,
                input_example=frame[columns].head(1).to_numpy(dtype=float),
                pip_requirements=["scikit-learn>=1.5", "pandas>=2.2", "mlflow>=2.19,<3"],
            )
            run_id = run.info.run_id
        version = _latest_version(client)
        if version is None or version.run_id != run_id:
            raise RuntimeError("MLflow did not register the model version for this run")
        for key, value in (("trigger", trigger), ("trigger_ref", trigger_ref or ""), ("trained_at", trained_at)):
            client.set_model_version_tag(REGISTERED_NAME, version.version, key, value)
        version = client.get_model_version(REGISTERED_NAME, version.version)
    registry = _registry_record(version)
    registry["run_id"] = run_id
    return _response(model, evaluation, registry, data, rules, as_of)


def serve(data: dict, rules: dict, as_of: date) -> dict:
    """Score with the latest registered model, training the first version if none exists."""
    loaded = load_latest()
    if loaded is None:
        return publish(data, rules, as_of, "bootstrap", None)
    model, evaluation, registry = loaded
    return _response(model, evaluation, registry, data, rules, as_of)


def _response(model, evaluation: dict, registry: dict, data: dict, rules: dict, as_of: date) -> dict:
    report = {**evaluation, "current": score_current(model, data, rules, as_of, evaluation["features"]), "registry": registry}
    note = "The shadow score comes from the MLflow model registered for this upload. The next CSV upload trains and registers a new version."
    if note not in report["caveats"]:
        report["caveats"] = [*report["caveats"], note]
    return report


def retrain_quietly(engine, rules: dict, as_of: date, batch_id: str) -> None:
    """Background hook for a successful upload. A failed fit keeps the previous version."""
    from .service import load_current_frames

    try:
        with engine.connect() as conn:
            frames = load_current_frames(conn)
        if frames["vessels"].empty:
            return
        publish(frames, rules, as_of, "upload", batch_id)
    except Exception:
        log.exception("shadow model was not retrained; the previous MLflow version stays registered")
