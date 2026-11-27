"""Load the sample CSVs through the same validation and versioning path as the upload endpoint."""

import argparse
import sys
from pathlib import Path

from sqlalchemy import func, select

from app import service
from app.config import get_settings
from app.db import get_engine, uploads
from app.schemas import TABLE_SPECS
from app.scoring import load_rules
from app.upload import UploadRejected, save_upload, validate_upload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("data_dir", type=Path)
    parser.add_argument("--force", action="store_true", help="load even if data was already uploaded")
    args = parser.parse_args()

    files = []
    for spec in TABLE_SPECS.values():
        path = args.data_dir / f"{spec.file_stem}.csv"
        if not path.exists():
            print(f"Missing {path}", file=sys.stderr)
            return 1
        files.append((path.name, path.read_bytes()))

    settings = get_settings()
    with get_engine().begin() as conn:
        if not args.force and conn.execute(select(func.count()).select_from(uploads)).scalar():
            print("Data already loaded; use --force to load a new version.")
            return 0
        try:
            batch = validate_upload(conn, files)
        except UploadRejected as exc:
            for e in exc.errors:
                print(f"{e.file}:{e.row} {e.column}: {e.message} ({e.value!r})", file=sys.stderr)
            return 1
        saved = save_upload(conn, batch, "ingest")
        calc = service.recalculate(conn, load_rules(settings.rules_path), settings.today(), "upload", saved["batch_id"], "ingest")
        service.log_event(conn, "upload", "ingest", {"batch_id": saved["batch_id"], "files": saved["files"]})

    for f in saved["files"]:
        print(f"{f['file_name']}: {f['row_count']} rows (upload {f['upload_id']})")
    print(f"Scored {len(calc['results'])} vessels; actions {calc['actions']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
