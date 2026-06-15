"""ChromaDB manager with Ollama embeddings."""

from __future__ import annotations

import logging
from pathlib import Path

import chromadb

from knowledge_base.kb_embeddings import OllamaEmbeddingFunction

logger = logging.getLogger(__name__)

CHROMA_PATH = Path(__file__).parent / "chroma_db"
COLLECTION_NAME = "software_patterns"


class KBManager:
    """Vector store for software development patterns."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        self.client = chromadb.PersistentClient(path=str(CHROMA_PATH))
        self.ef = OllamaEmbeddingFunction(
            model="nomic-embed-text",
            base_url="http://localhost:11434",
        )
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=self.ef,
            metadata={"hnsw:space": "cosine"},
        )

    def count(self) -> int:
        return self.collection.count()

    def add_document(self, doc_id: str, content: str, metadata: dict) -> None:
        self.collection.add(
            ids=[doc_id],
            documents=[content],
            metadatas=[metadata],
        )

    def search(
        self,
        query: str,
        n_results: int = 3,
        where: dict | None = None,
    ) -> list[dict]:
        if self.count() == 0:
            return []

        kwargs: dict = {
            "query_texts": [query],
            "n_results": min(n_results, self.count()),
        }
        if where:
            kwargs["where"] = where

        raw = self.collection.query(**kwargs)
        results: list[dict] = []

        if not raw["documents"] or not raw["documents"][0]:
            return results

        for i, doc in enumerate(raw["documents"][0]):
            distance = raw["distances"][0][i] if raw.get("distances") else 1.0
            score = max(0.0, 1.0 - distance)
            metadata = raw["metadatas"][0][i] if raw.get("metadatas") else {}
            results.append(
                {
                    "content": doc,
                    "score": score,
                    "metadata": metadata or {},
                }
            )

        return results
