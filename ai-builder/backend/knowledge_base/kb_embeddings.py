"""Ollama embeddings for ChromaDB."""

from __future__ import annotations

import logging
import os

import httpx
from chromadb.api.types import EmbeddingFunction, Embeddings

logger = logging.getLogger(__name__)


class OllamaEmbeddingFunction(EmbeddingFunction):
    """Embeddings locales con Ollama nomic-embed-text."""

    def __init__(
        self,
        model: str = "nomic-embed-text",
        base_url: str | None = None,
    ):
        self.model = model
        self.base_url = (base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")).rstrip("/")

    def _embed_one(self, text: str) -> list[float]:
        # Ollama >= 0.3 uses /api/embed; older versions use /api/embeddings
        try:
            response = httpx.post(
                f"{self.base_url}/api/embed",
                json={"model": self.model, "input": text},
                timeout=60.0,
            )
            if response.status_code == 404:
                raise httpx.HTTPStatusError("fallback", request=response.request, response=response)
            response.raise_for_status()
            data = response.json()
            if "embeddings" in data and data["embeddings"]:
                return data["embeddings"][0]
            if "embedding" in data:
                return data["embedding"]
        except httpx.HTTPStatusError:
            response = httpx.post(
                f"{self.base_url}/api/embeddings",
                json={"model": self.model, "prompt": text},
                timeout=60.0,
            )
            response.raise_for_status()
            return response.json()["embedding"]

        raise ValueError(f"No embedding returned for model {self.model}")

    def __call__(self, input: list[str]) -> Embeddings:
        return [list(self._embed_one(text)) for text in input]

    def embed_query(self, input: str) -> Embeddings:
        return [self._embed_one(input)]
