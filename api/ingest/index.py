"""Write the synthetic reports and bring the evidence collection in step with PostgreSQL."""

import json
import logging
import sys

from app.db import get_engine
from app.indexer import run_indexing
from app.rag import ai_status


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    status = ai_status()
    if not status["enabled"]:
        print(f"Skipping evidence indexing: {status['reason']}. Scores and actions work without it.")
        return 0
    stats = run_indexing(get_engine(), include_reports=True, actor="ingest")
    print(json.dumps(stats, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
