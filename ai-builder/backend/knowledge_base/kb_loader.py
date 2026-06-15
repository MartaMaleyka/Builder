"""Load markdown documents into ChromaDB."""

import logging
from pathlib import Path

from knowledge_base.kb_manager import KBManager

logger = logging.getLogger(__name__)

DOCUMENTS_PATH = Path(__file__).parent / "documents"


def _infer_type(file_path: Path) -> str:
    parts = file_path.parts
    if "frontend" in parts:
        return "component"
    if "backend" in parts:
        return "architecture"
    if "database" in parts:
        return "architecture"
    if "auth" in parts:
        return "architecture"
    return "config"


def init_knowledge_base() -> None:
    """Index documents from knowledge_base/documents/ if the collection is empty."""
    kb = KBManager()

    if kb.count() > 0:
        print(f"[KB] Already indexed ({kb.count()} docs), skipping")
        return

    if not DOCUMENTS_PATH.exists():
        print("[KB] No documents folder found, skipping indexing")
        return

    md_files = sorted(DOCUMENTS_PATH.rglob("*.md"))
    if not md_files:
        print("[KB] No markdown documents found")
        return

    print(f"[KB] Indexing {len(md_files)} documents with Ollama embeddings...")
    indexed = 0
    for md_file in md_files:
        try:
            content = md_file.read_text(encoding="utf-8")
            rel_path = md_file.relative_to(DOCUMENTS_PATH)
            doc_id = str(rel_path).replace("/", "_").replace("\\", "_")
            metadata = {
                "type": _infer_type(md_file),
                "source": str(rel_path),
                "concept": md_file.stem,
            }
            kb.add_document(doc_id, content, metadata)
            indexed += 1
            logger.info("[KB] Indexed: %s", rel_path)
        except Exception as exc:
            logger.warning("[KB] Failed to index %s: %s", md_file, exc)

    if indexed == 0:
        print("[KB] Warning: no documents indexed — run: ollama pull nomic-embed-text")
    else:
        print(f"[KB] Indexed {indexed} documents")
