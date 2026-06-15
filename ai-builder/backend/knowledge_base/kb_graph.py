"""Knowledge graph of software development concepts."""

import json
from pathlib import Path

import networkx as nx

GRAPH_PATH = Path(__file__).parent / "knowledge_graph.json"


class KnowledgeGraph:
    """
    Grafo de relaciones entre conceptos de software.
    Nodos: conceptos (sidebar, repository, auth, etc.)
    Edges: relaciones (requires, relates_to, implements, extends)
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        self.graph = nx.DiGraph()
        if GRAPH_PATH.exists():
            self._load()
        else:
            self._build_default_graph()
            self._save()
        print(
            f"[Graph] Loaded: {self.graph.number_of_nodes()} nodes, "
            f"{self.graph.number_of_edges()} edges"
        )

    def _build_default_graph(self):
        nodes = [
            ("sidebar", {"cat": "frontend", "desc": "navigation sidebar component"}),
            ("navbar", {"cat": "frontend", "desc": "top navigation bar"}),
            ("layout", {"cat": "frontend", "desc": "page layout wrapper"}),
            ("data_table", {"cat": "frontend", "desc": "table with CRUD actions"}),
            ("card_grid", {"cat": "frontend", "desc": "responsive card grid"}),
            ("modal_form", {"cat": "frontend", "desc": "modal dialog with form"}),
            ("stats_bar", {"cat": "frontend", "desc": "metrics summary row"}),
            ("empty_state", {"cat": "frontend", "desc": "empty list placeholder"}),
            ("skeleton", {"cat": "frontend", "desc": "loading skeleton"}),
            ("form_input", {"cat": "frontend", "desc": "form field with validation"}),
            ("badge", {"cat": "frontend", "desc": "status pill badge"}),
            ("routing", {"cat": "frontend", "desc": "react router setup"}),
            ("hooks", {"cat": "frontend", "desc": "custom react hooks"}),
            ("context", {"cat": "frontend", "desc": "react context state"}),
            ("repository", {"cat": "backend", "desc": "database query layer"}),
            ("service", {"cat": "backend", "desc": "business logic layer"}),
            ("controller", {"cat": "backend", "desc": "HTTP request handler"}),
            ("routes", {"cat": "backend", "desc": "express route definitions"}),
            ("middleware", {"cat": "backend", "desc": "express middleware"}),
            ("error_handler", {"cat": "backend", "desc": "global error handling"}),
            ("validator", {"cat": "backend", "desc": "input validation"}),
            ("auth", {"cat": "backend", "desc": "authentication logic"}),
            ("jwt", {"cat": "backend", "desc": "JSON web tokens"}),
            ("crud", {"cat": "backend", "desc": "create read update delete"}),
            ("sqlite", {"cat": "database", "desc": "SQLite with better-sqlite3"}),
            ("postgres", {"cat": "database", "desc": "PostgreSQL database"}),
            ("migration", {"cat": "database", "desc": "database migrations"}),
            ("seed", {"cat": "database", "desc": "seed data scripts"}),
            ("schema", {"cat": "database", "desc": "database schema design"}),
            ("docker", {"cat": "config", "desc": "Docker containerization"}),
            ("vite", {"cat": "config", "desc": "Vite build tool"}),
            ("tailwind", {"cat": "config", "desc": "Tailwind CSS"}),
            ("express", {"cat": "config", "desc": "Express.js server"}),
            ("fastapi", {"cat": "config", "desc": "FastAPI Python server"}),
            ("mvc", {"cat": "pattern", "desc": "Model View Controller"}),
            ("clean_arch", {"cat": "pattern", "desc": "Clean Architecture"}),
            ("rest_api", {"cat": "pattern", "desc": "RESTful API design"}),
        ]
        self.graph.add_nodes_from(nodes)

        edges = [
            ("layout", "sidebar", "contains", 1.0),
            ("layout", "navbar", "contains", 1.0),
            ("sidebar", "routing", "requires", 0.9),
            ("navbar", "routing", "requires", 0.9),
            ("routing", "hooks", "uses", 0.7),
            ("data_table", "modal_form", "triggers", 0.9),
            ("data_table", "empty_state", "shows", 0.8),
            ("data_table", "skeleton", "shows", 0.8),
            ("data_table", "badge", "contains", 0.7),
            ("card_grid", "modal_form", "triggers", 0.9),
            ("card_grid", "empty_state", "shows", 0.8),
            ("card_grid", "skeleton", "shows", 0.8),
            ("card_grid", "badge", "contains", 0.7),
            ("modal_form", "form_input", "contains", 1.0),
            ("modal_form", "validator", "uses", 0.8),
            ("stats_bar", "hooks", "uses", 0.7),
            ("clean_arch", "repository", "implements", 1.0),
            ("clean_arch", "service", "implements", 1.0),
            ("clean_arch", "controller", "implements", 1.0),
            ("controller", "service", "calls", 1.0),
            ("service", "repository", "calls", 1.0),
            ("repository", "sqlite", "queries", 0.8),
            ("repository", "postgres", "queries", 0.8),
            ("routes", "controller", "calls", 1.0),
            ("routes", "middleware", "uses", 0.9),
            ("routes", "validator", "uses", 0.8),
            ("auth", "jwt", "uses", 1.0),
            ("auth", "middleware", "implements", 1.0),
            ("middleware", "error_handler", "includes", 0.8),
            ("routes", "auth", "protected_by", 0.7),
            ("crud", "repository", "uses", 1.0),
            ("crud", "service", "uses", 1.0),
            ("crud", "controller", "uses", 1.0),
            ("crud", "data_table", "displayed_in", 0.8),
            ("schema", "migration", "versioned_by", 0.8),
            ("schema", "seed", "populated_by", 0.8),
            ("sqlite", "seed", "uses", 0.7),
            ("postgres", "migration", "uses", 0.9),
            ("vite", "tailwind", "integrates", 1.0),
            ("vite", "routing", "supports", 0.7),
            ("express", "routes", "mounts", 1.0),
            ("express", "middleware", "uses", 1.0),
            ("docker", "express", "runs", 0.8),
            ("docker", "fastapi", "runs", 0.8),
            ("mvc", "controller", "implements", 1.0),
            ("mvc", "service", "implements", 0.8),
            ("mvc", "repository", "implements", 0.9),
            ("rest_api", "routes", "defines", 1.0),
            ("rest_api", "controller", "handled_by", 1.0),
            ("rest_api", "crud", "exposes", 0.9),
        ]

        for src, dst, rel, weight in edges:
            self.graph.add_edge(src, dst, relation=rel, weight=weight)

    def get_related(self, concept: str, depth: int = 2) -> list[str]:
        if concept not in self.graph:
            matches = [n for n in self.graph.nodes if concept.lower() in n]
            if not matches:
                return []
            concept = matches[0]

        related: dict[str, float] = {}
        queue = [(concept, 1.0, 0)]
        visited = {concept}

        while queue:
            node, weight, d = queue.pop(0)
            if d >= depth:
                continue
            for neighbor in self.graph.successors(node):
                if neighbor not in visited:
                    edge_weight = self.graph[node][neighbor].get("weight", 0.5)
                    accumulated = weight * edge_weight
                    related[neighbor] = max(related.get(neighbor, 0), accumulated)
                    visited.add(neighbor)
                    queue.append((neighbor, accumulated, d + 1))

        return sorted(related.keys(), key=lambda x: related[x], reverse=True)

    def get_required_components(self, feature: str) -> list[str]:
        feature_map = {
            "crud": ["crud"],
            "auth": ["auth", "middleware", "jwt"],
            "dashboard": ["stats_bar", "card_grid", "hooks"],
            "list": ["data_table", "empty_state", "skeleton"],
            "form": ["modal_form", "form_input", "validator"],
            "navigation": ["sidebar", "routing", "layout"],
            "api": ["rest_api", "routes", "controller"],
        }
        concepts = feature_map.get(feature.lower(), [feature.lower()])
        result = set(concepts)
        for c in concepts:
            result.update(self.get_related(c, depth=1))
        return list(result)

    def explain_path(self, src: str, dst: str) -> str:
        try:
            path = nx.shortest_path(self.graph, src, dst)
            steps = []
            for i in range(len(path) - 1):
                rel = self.graph[path[i]][path[i + 1]].get("relation", "relates_to")
                steps.append(f"{path[i]} --[{rel}]--> {path[i + 1]}")
            return " | ".join(steps)
        except nx.NetworkXNoPath:
            return f"No direct path between {src} and {dst}"

    def _save(self):
        data = nx.node_link_data(self.graph)
        GRAPH_PATH.write_text(json.dumps(data, indent=2))

    def _load(self):
        data = json.loads(GRAPH_PATH.read_text())
        self.graph = nx.node_link_graph(data, directed=True)
