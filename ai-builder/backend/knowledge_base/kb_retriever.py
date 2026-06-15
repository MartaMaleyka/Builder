"""RAG retriever combining ChromaDB semantic search with knowledge graph."""

from knowledge_base.kb_graph import KnowledgeGraph
from knowledge_base.kb_manager import KBManager


class KBRetriever:
    def __init__(self):
        self.kb = KBManager()
        self.graph = KnowledgeGraph()

    def get_context_for_file(self, file_path: str, prd) -> str:
        """Contexto inteligente para un archivo específico."""
        contexts = []
        fname = file_path.split("/")[-1].replace(".jsx", "").replace(".js", "").replace(".tsx", "")

        semantic_results = self.kb.search(query=f"{fname} {file_path}", n_results=2)
        if semantic_results:
            contexts.append(self._format("Semantic Match", semantic_results))

        related_concepts = self.graph.get_related(fname, depth=2)
        if related_concepts:
            for concept in related_concepts[:3]:
                results = self.kb.search(query=concept, n_results=1)
                if results and results[0]["score"] > 0.4:
                    contexts.append(self._format(f"Related: {concept}", results))

        if file_path.endswith((".jsx", ".tsx")):
            contexts.append(self._get_frontend_context(fname))
        elif "repository" in file_path:
            contexts.append(self._get_backend_context("repository", prd))
        elif "service" in file_path:
            contexts.append(self._get_backend_context("service", prd))
        elif "controller" in file_path:
            contexts.append(self._get_backend_context("controller", prd))
        elif "server" in file_path or "app" in file_path:
            contexts.append(self._get_backend_context("express", prd))

        return "\n\n---\n\n".join(c for c in contexts if c.strip())

    def get_context_for_module(self, module_name: str, prd) -> str:
        """Contexto de alto nivel para un módulo completo."""
        contexts = []

        if module_name == "frontend_core":
            required = self.graph.get_required_components("navigation")
            required += self.graph.get_required_components("crud")
            for concept in set(required[:5]):
                results = self.kb.search(query=concept, n_results=1)
                if results:
                    contexts.append(self._format(concept, results))

        elif module_name == "backend_core":
            required = self.graph.get_required_components("api")
            for concept in set(required[:4]):
                results = self.kb.search(query=concept, n_results=1)
                if results:
                    contexts.append(self._format(concept, results))

        elif module_name == "data_models":
            results = self.kb.search(
                query=f"database schema {prd.proposed_stack.database}",
                n_results=2,
            )
            contexts.append(self._format("Schema Pattern", results))

        elif module_name == "auth":
            path = self.graph.explain_path("auth", "middleware")
            results = self.kb.search(query="authentication JWT middleware", n_results=2)
            contexts.append(f"Auth dependency chain: {path}")
            contexts.append(self._format("Auth Pattern", results))

        return "\n\n---\n\n".join(c for c in contexts if c.strip())

    def _get_frontend_context(self, component_name: str) -> str:
        component_type = "component"
        name_lower = component_name.lower()
        if any(x in name_lower for x in ["app", "layout", "main"]):
            component_type = "sidebar layout navigation"
        elif any(x in name_lower for x in ["page", "list", "view"]):
            component_type = "data table CRUD empty state"
        elif any(x in name_lower for x in ["form", "modal", "edit"]):
            component_type = "modal form validation"
        elif any(x in name_lower for x in ["dashboard", "stats", "home"]):
            component_type = "stats bar metrics cards"

        results = self.kb.search(
            query=component_type,
            n_results=2,
            where={"type": "component"},
        )
        return self._format(f"Component Pattern: {component_type}", results)

    def _get_backend_context(self, layer: str, prd) -> str:
        db = str(prd.proposed_stack.database).lower()
        results = self.kb.search(
            query=f"{layer} pattern {db}",
            n_results=2,
            where={"type": {"$in": ["architecture", "config"]}},
        )
        return self._format(f"Backend Pattern: {layer}", results)

    def _format(self, title: str, results: list) -> str:
        if not results:
            return ""
        parts = [f"### {title}"]
        for r in results:
            if r.get("score", 0) > 0.25:
                parts.append(r["content"][:1500])
        return "\n\n".join(parts)
