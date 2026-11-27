"""Score evidence retrieval against eval/golden.yaml, with and without reranking."""

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from ragwire.eval import GoldenSet, sweep

from app import evidence
from app.config import API_DIR
from app.db import get_engine
from app.rag import ai_status, get_store
from app.upload import current_data_version


def make_retrieve(store, version, leaks: list):
    def retrieve(query: str, top_k: int = 5, filters: dict | None = None, rerank: bool = True):
        f = dict(filters or {})
        vessel_id = f.pop("vessel_id")
        flt = evidence.build_filter(vessel_id, version, evidence.EvidenceFilters(
            source_type=f.get("source_type"), table=f.get("table"), doc_type=f.get("doc_type"),
            status=f.get("status"), category=f.get("category"),
            date_from=date.fromisoformat(f["from"]) if f.get("from") else None,
            date_to=date.fromisoformat(f["to"]) if f.get("to") else None))
        docs = evidence.search(store if rerank else _without_rerank(store), query, flt, top_k)
        leaks.extend((vessel_id, d.metadata.get("evidence_id")) for d in docs if d.metadata.get("vessel_id") != vessel_id)
        return docs
    return retrieve


def _without_rerank(store):
    from dataclasses import replace
    return replace(store, reranker=None)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--golden", type=Path, default=API_DIR / "eval" / "golden.yaml")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--out", type=Path, default=API_DIR / "eval" / "results.json")
    args = parser.parse_args()

    status = ai_status()
    if not status["enabled"]:
        print(f"Cannot evaluate: {status['reason']}", file=sys.stderr)
        return 1
    store = get_store()
    with get_engine().connect() as conn:
        version = current_data_version(conn)
    golden = GoldenSet.from_file(args.golden)
    leaks: list = []
    result = sweep(store, golden, {"hybrid": {"rerank": False}, "hybrid + rerank": {"rerank": True}},
                   top_k=args.top_k, retrieve=make_retrieve(store, version, leaks))
    print(result)
    for run in result.results:
        print(run.to_table())
    if leaks:
        print(f"FAIL: retrieved other vessels' evidence: {leaks[:10]}", file=sys.stderr)
        return 1
    question = "Why was this vessel detained?"
    docs = evidence.search(store, question, evidence.build_filter("V001", version), 5)
    grounded = evidence.answer(store, question, docs)
    print(f"V001 detention answer (refused={grounded['refused']}): {grounded['answer']}")
    args.out.write_text(json.dumps({
        "top_k": args.top_k, "queries": len(golden),
        "v001_detention": {"refused": grounded["refused"], "answer": grounded["answer"],
                           "citations": [c["evidence_id"] for c in grounded["citations"]]},
        "runs": {r.label: {"metrics": r.metrics,
                           "per_query": [{"query": q.query, "recall": q.metrics["recall"],
                                          "missed": q.missed, "retrieved": q.retrieved}
                                         for q in r.per_query]}
                 for r in result.results},
    }, indent=1), encoding="utf-8")
    print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
