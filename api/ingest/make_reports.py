"""Write the synthetic inspection reports and manifest from the current PostgreSQL data, without indexing."""

import argparse
import sys
from pathlib import Path

from app import service
from app.config import get_settings
from app.db import get_engine
from app.reports import build_reports, write_reports


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=get_settings().reports_dir)
    args = parser.parse_args()
    with get_engine().connect() as conn:
        frames = service.load_current_frames(conn)
    if frames["vessels"].empty:
        print("No data loaded yet.", file=sys.stderr)
        return 1
    print(write_reports(args.out, build_reports(frames)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
