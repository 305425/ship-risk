"""Evidence search for one vessel: code-built Qdrant filters, hybrid search, rerank, cited answer.

The vessel always comes from the caller (the route), never from the question,
so no wording can widen a search to another ship.
"""

from dataclasses import dataclass
from datetime import date

from langchain_core.documents import Document
from qdrant_client import models

from langsmith import traceable

from .rag import EvidenceStore
from .reports import date_num
from .tracing import answer_inputs, configure_tracing

NO_EVIDENCE = "No supporting document found for this vessel."
SOURCE_TYPES = ("record", "report", "vessel_summary")
SNIPPET_CHARS = 400


@dataclass(frozen=True)
class EvidenceFilters:
    source_type: str | None = None
    table: str | None = None
    doc_type: str | None = None
    status: str | None = None
    category: str | None = None
    date_from: date | None = None
    date_to: date | None = None

    def as_dict(self) -> dict:
        return {k: (v.isoformat() if isinstance(v, date) else v) for k, v in self.__dict__.items() if v is not None}


def _match(key: str, value) -> models.FieldCondition:
    return models.FieldCondition(key=f"metadata.{key}", match=models.MatchValue(value=value))


def build_filter(vessel_id: str | None, version: dict, f: EvidenceFilters = EvidenceFilters()) -> models.Filter:
    """Filter for evidence.

    Record points must belong to the current upload of their table, so rows
    from superseded uploads are never returned while re-indexing catches up.
    A vessel id limits the filter to that ship. The fleet chat leaves it empty.
    """
    current_uploads = [u for u in version.values() if u is not None]
    must: list = [
        models.Filter(should=[
            models.FieldCondition(key="metadata.source_type",
                                  match=models.MatchAny(any=["report", "vessel_summary"])),
            models.FieldCondition(key="metadata.upload_id", match=models.MatchAny(any=current_uploads or [-1])),
        ]),
    ]
    if vessel_id:
        must.insert(0, _match("vessel_id", vessel_id))
    if f.source_type:
        must.append(_match("source_type", f.source_type))
    if f.table:
        must.append(_match("table", f.table))
    if f.doc_type:
        must.append(_match("doc_type", f.doc_type))
    if f.status:
        must.append(_match("status", f.status.strip().lower()))
    if f.category:
        must.append(_match("category", f.category.strip().lower()))
    if f.date_from or f.date_to:
        must.append(models.FieldCondition(key="metadata.date_num", range=models.Range(
            gte=date_num(f.date_from) if f.date_from else None,
            lte=date_num(f.date_to) if f.date_to else None)))
    return models.Filter(must=must)


def search(store: EvidenceStore, query: str, flt: models.Filter, k: int = 5) -> list[Document]:
    fetch = max(store.fetch_k, k) if store.reranker else k
    docs = store.vectorstore.similarity_search(query, k=fetch, filter=flt)
    if store.reranker and docs:
        docs = store.reranker.rerank(query, docs, top_n=k)
    return docs[:k]


def _for_generation(doc: Document) -> Document:
    m = doc.metadata
    return Document(page_content=doc.page_content,
                    metadata={**m, "source": m.get("label") or m.get("evidence_id", "unknown")})


def citation(doc: Document, index: int | None = None) -> dict:
    m = doc.metadata
    return {
        "index": index,
        "evidence_id": m.get("evidence_id"),
        "label": m.get("label"),
        "source_type": m.get("source_type"),
        "table": m.get("table"),
        "doc_type": m.get("doc_type"),
        "record_id": m.get("record_id"),
        "vessel_id": m.get("vessel_id"),
        "date": m.get("date"),
        "status": m.get("status"),
        "category": m.get("category"),
        "synthetic": bool(m.get("synthetic", False)),
        "rerank_score": m.get("rerank_score"),
        "snippet": doc.page_content[:SNIPPET_CHARS],
    }


@traceable(name="ragwire.generate", run_type="chain", process_inputs=answer_inputs)
def answer(store: EvidenceStore, query: str, docs: list[Document]) -> dict:
    """Cited answer, or a refusal when retrieval or the model finds nothing to stand on."""
    configure_tracing()
    if not docs:
        return {"refused": True, "answer": NO_EVIDENCE, "citations": [], "evidence_coverage": 0.0}
    result = store.generator.generate(query, [_for_generation(d) for d in docs])
    if result.refused:
        return {"refused": True, "answer": NO_EVIDENCE, "citations": [], "evidence_coverage": 0.0}
    return {
        "refused": False,
        "answer": result.text,
        "citations": [citation(docs[c.index - 1], c.index) for c in result.citations],
        "evidence_coverage": round(result.confidence, 2),
    }
