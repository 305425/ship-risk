"""Evidence filters, synthetic reports and the evidence endpoint.

Qdrant tests use deterministic hash embeddings, so they check filters and
re-indexing rather than whether a question ranks the right sentence first.
"""

import hashlib
import os
from datetime import date

import pytest
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from qdrant_client import QdrantClient, models
from ragwire.generation.answer import Answer, Citation

from app import evidence, rag
from app.evidence import NO_EVIDENCE
from app.indexer import fingerprint, row_documents, sync_points
from app.rag import EvidenceStore
from app.reports import build_reports

class HashEmbeddings(Embeddings):
    def __init__(self, size: int = 32):
        self.size = size

    def _vec(self, text: str) -> list[float]:
        raw = hashlib.sha256(text.encode()).digest()
        buf = bytearray()
        while len(buf) < self.size:
            raw = hashlib.sha256(raw).digest()
            buf.extend(raw)
        return [byte / 127.5 - 1 for byte in buf[: self.size]]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vec(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vec(text)


def _subset(sample, vessels: set[str]) -> dict:
    return {table: frame[frame.vessel_id.isin(vessels)].reset_index(drop=True) for table, frame in sample.items()}


def test_reports_carry_inspection_identity(sample):
    reports = build_reports(sample)
    inspections = sample["inspections"].set_index("inspection_id")
    assert len(reports) == len(inspections) == 80
    for name, (text, meta) in reports.items():
        ins = inspections.loc[meta["inspection_id"]]
        assert name == f"{meta['inspection_id']}.md"
        assert meta["vessel_id"] == ins.vessel_id
        assert meta["record_id"] == meta["inspection_id"]
        assert meta["evidence_id"] == f"report:{meta['inspection_id']}"
        assert meta["date"] == ins.inspection_date.isoformat()
        assert meta["category"] == ins.inspection_authority.lower()
        assert meta["synthetic"] is True
        assert "SYNTHETIC REPORT" in text


@pytest.fixture(scope="module")
def qdrant_store(sample):
    url = os.environ.get("QDRANT_TEST_URL", "http://localhost:56333")
    try:
        client = QdrantClient(url=url, timeout=30)
        client.get_collections()
    except Exception as exc:
        pytest.skip(f"Qdrant is not available at {url}: {exc}")
    name = "ship-risk-pytest"
    if client.collection_exists(name):
        client.delete_collection(name)
    client.create_collection(name, vectors_config=models.VectorParams(size=32, distance=models.Distance.COSINE))
    from langchain_qdrant import QdrantVectorStore

    store = EvidenceStore(
        client=client, collection=name,
        vectorstore=QdrantVectorStore(client=client, collection_name=name, embedding=HashEmbeddings()),
        generator=None, reranker=None, model="hash", prompt_version="test",
    )
    frames = _subset(sample, {"V001", "V004"})
    version = {table: 1 for table in frames}
    first = sync_points(store, row_documents(frames, version), "record")
    assert first["embedded"] == first["total"] > 0
    yield store, frames, version
    client.delete_collection(name)


def _search(store, query, vessel, version, **kwargs):
    filters = evidence.EvidenceFilters(**kwargs)
    return evidence.search(store, query, evidence.build_filter(vessel, version, filters), k=10)


@pytest.mark.qdrant
def test_vessel_filter_excludes_other_ships(qdrant_store):
    store, _, version = qdrant_store
    docs = _search(store, "Why was the vessel detained?", "V001", version)
    assert docs
    assert {d.metadata["vessel_id"] for d in docs} == {"V001"}
    assert "detentions:INS0016" not in {d.metadata["evidence_id"] for d in docs}


@pytest.mark.qdrant
def test_status_and_date_filters_are_exact(qdrant_store):
    store, _, version = qdrant_store
    open_fire = _search(store, "fire pump", "V001", version, status="Open", category="Fire Safety")
    assert open_fire
    assert {d.metadata["status"] for d in open_fire} == {"open"}
    assert {d.metadata["category"] for d in open_fire} == {"fire safety"}

    ranged = _search(store, "inspection", "V001", version, table="inspections",
                     date_from=date(2025, 1, 1), date_to=date(2025, 6, 30))
    assert ranged
    assert {d.metadata["table"] for d in ranged} == {"inspections"}
    assert all(20250101 <= d.metadata["date_num"] <= 20250630 for d in ranged)


@pytest.mark.qdrant
def test_stale_upload_points_are_excluded(qdrant_store):
    store, frames, version = qdrant_store
    stale = {table: upload + 1 for table, upload in version.items()}
    assert _search(store, "detained fire pump", "V001", stale) == []
    assert _search(store, "detained fire pump", "V001", version)


@pytest.mark.qdrant
def test_unchanged_rows_are_not_reembedded(qdrant_store):
    store, frames, version = qdrant_store
    docs = row_documents(frames, version)
    again = sync_points(store, docs, "record")
    assert again["embedded"] == 0 and again["deleted"] == 0

    bumped = row_documents(frames, {table: upload + 5 for table, upload in version.items()})
    assert sync_points(store, bumped, "record")["embedded"] == 0

    changed = bumped[0]
    changed.page_content += " Revised wording."
    changed.metadata["fingerprint"] = fingerprint(changed.page_content, changed.metadata)
    assert sync_points(store, bumped, "record")["embedded"] == 1


@pytest.mark.db
def test_evidence_is_unavailable_without_a_provider_key(client, sample_files):
    from tests.test_api import upload

    assert upload(client, sample_files).status_code == 200
    uploads = client.get("/api/uploads").json()
    assert uploads and all(row["status"] == "index_pending" for row in uploads)
    response = client.get("/api/vessels/V001/evidence", params={"q": "Why was this vessel detained?"})
    assert response.status_code == 503
    assert client.get("/api/index/status").json()["enabled"] is False


@pytest.mark.db
def test_evidence_endpoint_refuses_and_stays_on_the_route_vessel(client, sample_files):
    from tests.test_api import upload

    assert upload(client, sample_files).status_code == 200
    class Capturing:
        def similarity_search(self, query, k=5, filter=None):
            self.filter = filter
            return []

    capturing = Capturing()
    rag.set_store(EvidenceStore(client=None, collection="fake", vectorstore=capturing, generator=None,
                                model="fake", prompt_version="test"))
    response = client.get("/api/vessels/V001/evidence", params={"q": "Why was V004 detained?"})
    assert response.status_code == 200
    body = response.json()
    assert body["refused"] is True and body["answer"] == NO_EVIDENCE and body["citations"] == []
    rendered = str(capturing.filter)
    assert "V001" in rendered and "V004" not in rendered


@pytest.mark.db
def test_evidence_endpoint_returns_citations(client, sample_files):
    from tests.test_api import upload

    assert upload(client, sample_files).status_code == 200
    doc = Document(
        page_content="V001 was detained on 2025-06-29 after inspection INS0004 for fire safety deficiencies.",
        metadata={"evidence_id": "report:INS0004", "label": "Inspection report INS0004 (synthetic)",
                  "source_type": "report", "vessel_id": "V001", "record_id": "INS0004", "synthetic": True},
    )

    class OneDoc:
        def similarity_search(self, query, k=5, filter=None):
            return [doc]

    class Citing:
        def generate(self, query, docs):
            return Answer("The vessel was detained for fire safety deficiencies [1].",
                          citations=[Citation(1, docs[0].metadata["source"], docs[0].page_content)],
                          refused=False, confidence=1.0)

    rag.set_store(EvidenceStore(client=None, collection="fake", vectorstore=OneDoc(), generator=Citing(),
                                model="fake", prompt_version="evidence-v1"))
    body = client.get("/api/vessels/V001/evidence", params={"q": "Why was this vessel detained?"}).json()
    assert body["refused"] is False
    assert body["citations"][0]["evidence_id"] == "report:INS0004"
    assert body["citations"][0]["record_id"] == "INS0004"
    assert body["citations"][0]["synthetic"] is True
