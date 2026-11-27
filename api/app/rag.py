"""RAGWire setup: provider config, code-set report metadata, payload indexes and local reranking."""

import json
import logging
import os
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from qdrant_client import QdrantClient, models
from ragwire import RAGWire
from ragwire.generation import AnswerGenerator
from ragwire.retriever.rerank import BaseReranker

from .config import Settings, get_settings

logger = logging.getLogger(__name__)

# The client defaults to 5 seconds, which a hybrid upsert of a full batch exceeds
# once the collection is indexing.
QDRANT_TIMEOUT_S = 120

MANIFEST_NAME = "manifest.json"

# Qdrant payload indexes. Everything not listed as integer is a keyword index.
# Dates are filtered through date_num (YYYYMMDD) because RAGWire re-creates
# indexes for every metadata key it sees and only knows integer/float/keyword.
FIELD_TYPES = {"date_num": "integer", "upload_id": "integer"}
FILTER_FIELDS = [
    "source_type", "vessel_id", "table", "doc_type", "status", "category",
    "evidence_id", "date_num", "upload_id",
]


class FastEmbedReranker(BaseReranker):
    """Cross-encoder reranking on ONNX Runtime, so no PyTorch in the image."""

    name = "fastembed_cross_encoder"

    def __init__(self, model_name: str = "Xenova/ms-marco-MiniLM-L-6-v2"):
        self.model_name = model_name
        self._model = None
        self._lock = threading.Lock()

    def _score(self, query: str, texts: list[str]) -> list[float]:
        with self._lock:
            if self._model is None:
                from fastembed.rerank.cross_encoder import TextCrossEncoder

                self._model = TextCrossEncoder(model_name=self.model_name)
        return [float(s) for s in self._model.rerank(query, texts)]


class ShipRiskRAG(RAGWire):
    """RAGWire whose report identity metadata comes from make_reports' manifest.

    The LLM extractor only adds descriptive tags; vessel, inspection, date and
    authority are laid over its output, so they cannot be mis-extracted.
    """

    def __init__(self, config_path: str | Path, reports_dir: str | Path):
        self.reports_dir = Path(reports_dir)
        super().__init__(str(config_path))
        self.llm_tagging = bool(self.config.get("metadata", {}).get("llm_tagging", True))
        self.vectorstore_wrapper.create_payload_indexes(FILTER_FIELDS, field_types=self._field_types)

    def _initialize_llm(self) -> None:
        super()._initialize_llm()
        self._field_types = {**self._field_types, **FIELD_TYPES}

    def _manifest(self) -> dict[str, dict]:
        path = self.reports_dir / MANIFEST_NAME
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}

    def _extract_metadata_with_retry(self, text: str, file_name: str) -> tuple:
        identity = self._manifest().get(file_name)
        if identity is None:
            logger.warning("No manifest entry for %s; it will be indexed without identity metadata", file_name)
            return {}, False
        if self.llm_tagging:
            tags, ok = super()._extract_metadata_with_retry(text, file_name)
        else:
            tags, ok = {}, True
        return {**tags, **identity}, ok


@dataclass
class EvidenceStore:
    """What evidence search and indexing need, independent of how it was built."""

    client: QdrantClient
    collection: str
    vectorstore: Any
    generator: AnswerGenerator | None
    reranker: BaseReranker | None = None
    fetch_k: int = 20
    model: str = ""
    prompt_version: str = ""
    rag: ShipRiskRAG | None = None
    extra: dict = field(default_factory=dict)


def relax_timeout(client: QdrantClient, seconds: int = QDRANT_TIMEOUT_S) -> None:
    remote = getattr(client, "_client", None)
    if remote is not None and getattr(remote, "_timeout", 0) < seconds:
        remote._timeout = seconds


def ensure_payload_indexes(client: QdrantClient, collection: str) -> None:
    for name in FILTER_FIELDS:
        schema = (models.PayloadSchemaType.INTEGER if FIELD_TYPES.get(name) == "integer"
                  else models.PayloadSchemaType.KEYWORD)
        client.create_payload_index(collection, f"metadata.{name}", field_schema=schema)


def build_store(settings: Settings) -> EvidenceStore:
    os.environ.setdefault("QDRANT_URL", settings.qdrant_url)
    os.environ.setdefault("REPORTS_DIR", str(settings.reports_dir))
    settings.reports_dir.mkdir(parents=True, exist_ok=True)
    rag = ShipRiskRAG(settings.rag_config_path, settings.reports_dir)
    relax_timeout(rag.vectorstore_wrapper.client)
    retriever_cfg = rag.config.get("retriever", {})
    rerank_model = retriever_cfg.get("local_rerank_model")
    return EvidenceStore(
        client=rag.vectorstore_wrapper.client,
        collection=rag.vectorstore_wrapper.collection_name,
        vectorstore=rag.vectorstore,
        generator=rag.generator,
        reranker=FastEmbedReranker(rerank_model) if rerank_model else None,
        fetch_k=int(retriever_cfg.get("fetch_k", 20)),
        model=rag.config.get("llm", {}).get("model", ""),
        prompt_version=rag.config.get("generation", {}).get("prompt_version", ""),
        rag=rag,
    )


_store: EvidenceStore | None = None
_store_lock = threading.Lock()


def ai_status(settings: Settings | None = None) -> dict:
    settings = settings or get_settings()
    missing = settings.llm_key_missing()
    return {
        "enabled": missing is None,
        "provider": settings.llm_provider,
        "reason": f"{missing} is not set" if missing else None,
    }


def get_store() -> EvidenceStore | None:
    """The shared store, or None when no provider key is configured.

    A store passed to set_store is returned as-is, which is how tests inject a
    fake. Connection failures raise and are not cached, so a Qdrant that comes
    up later is picked up on the next call.
    """
    global _store
    with _store_lock:
        if _store is not None:
            return _store
    settings = get_settings()
    if settings.llm_key_missing():
        return None
    with _store_lock:
        if _store is None:
            _store = build_store(settings)
        return _store


def set_store(store: EvidenceStore | None) -> None:
    global _store
    with _store_lock:
        _store = store
