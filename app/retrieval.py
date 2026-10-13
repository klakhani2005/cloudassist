"""Chunking + BM25 lexical retrieval.

BM25 ranks chunks by how often query terms appear, discounted for very common
terms (IDF) and normalized for chunk length. It is the standard lexical
baseline that dense/embedding retrievers are usually compared against.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import asdict, dataclass

TOKEN = re.compile(r"[a-z0-9]+")
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "can", "do", "does", "for", "from",
    "how", "i", "in", "is", "it", "of", "on", "or", "should", "that", "the", "this", "to",
    "what", "when", "where", "which", "who", "why", "with", "you", "your",
}


def tokenize(text: str) -> list[str]:
    return [t for t in TOKEN.findall(text.lower()) if t not in STOPWORDS]


@dataclass
class Chunk:
    source: str
    index: int
    text: str


class Retriever:
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1, self.b = k1, b
        self.chunks: list[Chunk] = []
        self._tf: list[Counter] = []
        self._df: Counter = Counter()
        self._avg_len = 0.0

    # ---- indexing -------------------------------------------------------
    def add_text(self, source: str, text: str, chunk_chars: int = 900, overlap: int = 120) -> int:
        """Chunk `text` and index it. Re-adding a source replaces its old chunks."""
        if overlap >= chunk_chars:
            raise ValueError("overlap must be smaller than chunk_chars")
        clean = re.sub(r"\s+", " ", text).strip()
        if not clean:
            return 0
        self.remove_source(source)
        start = index = 0
        while start < len(clean):
            end = min(len(clean), start + chunk_chars)
            # Try not to cut a word in half.
            if end < len(clean):
                space = clean.rfind(" ", start + chunk_chars // 2, end)
                end = space if space != -1 else end
            self.chunks.append(Chunk(source, index, clean[start:end].strip()))
            index += 1
            if end >= len(clean):
                break
            start = max(end - overlap, start + 1)
        self._rebuild()
        return index

    def remove_source(self, source: str) -> int:
        before = len(self.chunks)
        self.chunks = [c for c in self.chunks if c.source != source]
        if len(self.chunks) != before:
            self._rebuild()
        return before - len(self.chunks)

    def _rebuild(self) -> None:
        self._tf = [Counter(tokenize(c.text)) for c in self.chunks]
        self._df = Counter()
        for tf in self._tf:
            self._df.update(tf.keys())
        lengths = [sum(tf.values()) for tf in self._tf]
        self._avg_len = (sum(lengths) / len(lengths)) if lengths else 0.0

    # ---- search ---------------------------------------------------------
    def search(self, question: str, top_k: int = 3) -> list[tuple[Chunk, float]]:
        terms = set(tokenize(question))
        if not terms or not self.chunks:
            return []
        n = len(self.chunks)
        scored = []
        for chunk, tf in zip(self.chunks, self._tf):
            length = sum(tf.values()) or 1
            score = 0.0
            for term in terms:
                f = tf.get(term, 0)
                if not f:
                    continue
                idf = math.log(1 + (n - self._df[term] + 0.5) / (self._df[term] + 0.5))
                score += idf * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * length / self._avg_len))
            if score > 0:
                scored.append((chunk, score))
        scored.sort(key=lambda item: (-item[1], item[0].source, item[0].index))
        return scored[:top_k]

    # ---- persistence helpers -------------------------------------------
    def count(self) -> int:
        return len(self.chunks)

    def sources(self) -> list[str]:
        return sorted({c.source for c in self.chunks})

    def to_dict(self) -> dict:
        return {"chunks": [asdict(c) for c in self.chunks]}

    @classmethod
    def from_dict(cls, data: dict) -> "Retriever":
        r = cls()
        r.chunks = [Chunk(**c) for c in data.get("chunks", [])]
        r._rebuild()
        return r
