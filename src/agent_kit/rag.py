"""Retrieval: chunking + a dependency-free BM25 retriever, with a Vector
Search interface behind it.

RAG quality problems are usually chunking and evaluation problems, not
embedding-model problems — so the kit ships a transparent BM25 baseline you
can read and test. In a workspace, swap the retriever for a Databricks
Vector Search index (typically a Delta Sync index over a Unity Catalog
table) behind the same ``search(query, k)`` shape.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Protocol

_TOKEN = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


@dataclass
class Chunk:
    doc_id: str
    index: int
    text: str


@dataclass
class Document:
    doc_id: str
    text: str
    metadata: dict = field(default_factory=dict)


def chunk_text(text: str, chunk_size: int = 400, overlap: int = 80) -> list[str]:
    """Split text into overlapping character windows, preferring to break
    at a paragraph or sentence boundary near the window edge."""
    if chunk_size <= 0 or overlap < 0 or overlap >= chunk_size:
        raise ValueError("need 0 <= overlap < chunk_size")
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        if end < len(text):
            window = text[start:end]
            cut = max(window.rfind("\n\n"), window.rfind(". "))
            if cut > chunk_size // 2:
                end = start + cut + 1
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return chunks


class Retriever(Protocol):
    def search(self, query: str, k: int = 3) -> list[tuple[Chunk, float]]:
        ...


class BM25Retriever:
    """Classic Okapi BM25 over chunks. Deterministic, dependency-free."""

    def __init__(self, documents: list[Document], chunk_size: int = 400, overlap: int = 80,
                 k1: float = 1.5, b: float = 0.75) -> None:
        self.chunks: list[Chunk] = []
        for doc in documents:
            for i, piece in enumerate(chunk_text(doc.text, chunk_size, overlap)):
                self.chunks.append(Chunk(doc.doc_id, i, piece))
        self.k1, self.b = k1, b
        self._tf: list[Counter] = [Counter(tokenize(c.text)) for c in self.chunks]
        self._dl = [sum(tf.values()) for tf in self._tf]
        self._avgdl = (sum(self._dl) / len(self._dl)) if self._dl else 0.0
        df: Counter = Counter()
        for tf in self._tf:
            df.update(tf.keys())
        n = len(self.chunks)
        self._idf = {t: math.log(1 + (n - c + 0.5) / (c + 0.5)) for t, c in df.items()}

    def search(self, query: str, k: int = 3) -> list[tuple[Chunk, float]]:
        terms = tokenize(query)
        scored: list[tuple[Chunk, float]] = []
        for chunk, tf, dl in zip(self.chunks, self._tf, self._dl):
            score = 0.0
            for term in terms:
                if term not in tf:
                    continue
                freq = tf[term]
                denom = freq + self.k1 * (1 - self.b + self.b * dl / (self._avgdl or 1))
                score += self._idf.get(term, 0.0) * (freq * (self.k1 + 1)) / denom
            if score > 0:
                scored.append((chunk, round(score, 4)))
        scored.sort(key=lambda pair: pair[1], reverse=True)
        return scored[:k]


class DatabricksVectorSearchRetriever:
    """Interface stub for a Databricks Vector Search index.

    In a workspace this calls the Vector Search endpoint's similarity-search
    API (via the Databricks SDK, the optional ``databricks`` extra) against
    an index synced from a Unity Catalog table. The stub keeps the interface
    explicit and fails with instructions rather than silently falling back.
    """

    def __init__(self, endpoint: str, index_name: str) -> None:
        self.endpoint = endpoint
        self.index_name = index_name

    def search(self, query: str, k: int = 3) -> list[tuple[Chunk, float]]:
        try:
            import databricks.sdk  # noqa: F401
        except ImportError as exc:
            raise RuntimeError(
                "The Databricks Vector Search retriever needs a workspace + the "
                "Databricks SDK: pip install -e '.[databricks]'. "
                "Use BM25Retriever for offline development and evals."
            ) from exc
        raise NotImplementedError(
            f"Wire Vector Search similarity search for index {self.index_name} "
            f"on endpoint {self.endpoint} using the SDK in your workspace."
        )
