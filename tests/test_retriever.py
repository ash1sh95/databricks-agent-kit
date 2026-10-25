import pytest

from agent_kit import BM25Retriever, Document, chunk_text


def test_chunking_produces_overlap_and_covers_text():
    text = "Alpha sentence one. " * 60
    chunks = chunk_text(text, chunk_size=200, overlap=40)
    assert len(chunks) > 3
    assert all(len(c) <= 220 for c in chunks)
    assert "Alpha" in chunks[0]


def test_chunking_rejects_bad_overlap():
    with pytest.raises(ValueError):
        chunk_text("hello world", chunk_size=10, overlap=10)


def test_bm25_ranks_relevant_doc_first():
    docs = [
        Document("retention", "Data retention guideline: raw tables are kept for 90 days, "
                              "curated tables for 400 days."),
        Document("cost", "Cost optimisation: prefer serverless compute, auto-termination, "
                          "and owner tags on every job."),
        Document("patterns", "Agents call tools through Unity Catalog functions and are "
                             "traced in MLflow."),
    ]
    retriever = BM25Retriever(docs)
    hits = retriever.search("how long is data retention", k=1)
    assert hits and hits[0][0].doc_id == "retention"
    hits = retriever.search("serverless cost", k=1)
    assert hits and hits[0][0].doc_id == "cost"


def test_bm25_no_match_returns_empty():
    retriever = BM25Retriever([Document("a", "completely unrelated content here")])
    assert retriever.search("quantum chromodynamics") == []


def test_vector_search_stub_fails_with_instructions():
    from agent_kit.rag import DatabricksVectorSearchRetriever

    retriever = DatabricksVectorSearchRetriever("vs-endpoint", "main.agent_kit.docs_index")
    try:
        import databricks.sdk  # noqa: F401

        with pytest.raises(NotImplementedError):
            retriever.search("anything")
    except ImportError:
        with pytest.raises(RuntimeError, match="Vector Search"):
            retriever.search("anything")
