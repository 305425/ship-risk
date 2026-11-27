"""Container entrypoint: make the reports directory writable, then run as the app user."""

import os
import pwd
import shlex
import sys

def main() -> None:
    user = pwd.getpwnam("app")
    if user.pw_dir and user.pw_dir not in ("/", "/nonexistent"):
        os.makedirs(user.pw_dir, exist_ok=True)
        os.chown(user.pw_dir, user.pw_uid, user.pw_gid)
    reports = os.environ.get("REPORTS_DIR", "/app/reports")
    os.makedirs(reports, exist_ok=True)
    for directory, _dirs, files in os.walk(reports):
        os.chown(directory, user.pw_uid, user.pw_gid)
        for name in files:
            os.chown(os.path.join(directory, name), user.pw_uid, user.pw_gid)
    # Both the server and one-off index runs download ONNX models here.
    cache = os.environ.get("FASTEMBED_CACHE_PATH", "/var/cache/fastembed")
    os.makedirs(cache, exist_ok=True)
    os.chmod(cache, 0o1777)
    mlflow_dir = os.environ.get("MLFLOW_DIR", "/app/mlflow")
    os.makedirs(mlflow_dir, exist_ok=True)
    os.chown(mlflow_dir, user.pw_uid, user.pw_gid)
    os.chmod(mlflow_dir, 0o777)
    # MLflow's sqlite store creates this default root before an experiment artifact path is set.
    mlruns = "/app/mlruns"
    os.makedirs(mlruns, exist_ok=True)
    os.chown(mlruns, user.pw_uid, user.pw_gid)
    os.chmod(mlruns, 0o777)
    for path in (".chainlit", ".files"):
        os.makedirs(path, exist_ok=True)
        os.chown(path, user.pw_uid, user.pw_gid)
    command = " ".join(shlex.quote(arg) for arg in sys.argv[1:])
    os.execvp("su", ["su", "-s", "/bin/sh", "app", "-c", command])


if __name__ == "__main__":
    main()
