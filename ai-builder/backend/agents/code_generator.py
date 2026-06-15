"""Code Generator: produces a full project from an approved PRD."""

from __future__ import annotations

import asyncio
import logging
import re
from collections.abc import Callable
from typing import Optional

from langchain_core.messages import HumanMessage, SystemMessage

from agents.code_helpers import (
    all_generated_files,
    build_context_messages,
    finalize_result,
    init_generation_result,
    mark_module_failed,
    save_module_files,
    set_module_state,
)
from agents.code_llm import CodeLLMClient, code_llm, frontend_llm
from agents.frontend_qa_agent import FrontendQAAgent
from agents.code_prompts import build_module_prompt, module_plan
from agents.template_manager import TemplateManager
from knowledge_base.kb_retriever import KBRetriever
from models.schemas import (
    ClarifyContext,
    DockerfileParams,
    DockerComposeParams,
    EnvExampleParams,
    GeneratedFile,
    GenerationResult,
    ModuleFileOutput,
    ModuleState,
    ModuleStatus,
    PRDDocument,
    ReadmeParams,
)

logger = logging.getLogger(__name__)

generation_store: dict[str, GenerationResult] = {}

_TEMPLATE_MODULES = frozenset({"dockerfile", "docker_compose", "readme"})
_STRUCTURE_MODULE = "project_structure"
_SEED_MODULE = "seed"


def _filter_valid_files(files: list[ModuleFileOutput]) -> list[ModuleFileOutput]:
    """Skip directory entries and files with no content."""
    valid: list[ModuleFileOutput] = []
    for file in files:
        if file.path.endswith("/") or file.content.strip() == "":
            continue
        valid.append(file)
    return valid


def _is_typescript_stack(prd: PRDDocument) -> bool:
    return "typescript" in prd.proposed_stack.frontend.lower()


class CodeGenerator:
    """Generates a complete project module-by-module from an approved PRD."""

    def __init__(
        self,
        get_prd: Callable[[str], Optional[PRDDocument]],
        get_context: Callable[[str], Optional[ClarifyContext]],
    ) -> None:
        self._get_prd = get_prd
        self._get_context = get_context
        self._llm = CodeLLMClient()
        self._templates = TemplateManager()
        self._qa_agent = FrontendQAAgent()
        self._kb = KBRetriever()

    async def generate(self, session_id: str) -> GenerationResult:
        prd = self._get_prd(session_id)
        context = self._get_context(session_id)
        if prd is None:
            raise ValueError(f"No approved PRD for session {session_id}")
        if context is None:
            raise ValueError(f"No clarify context for session {session_id}")

        names = module_plan(prd, context)
        result = init_generation_result(session_id, names)
        generation_store[session_id] = result.model_copy(deep=True)

        completed: list[ModuleStatus] = []
        for module_name in names:
            if module_name == _STRUCTURE_MODULE:
                continue

            set_module_state(result, module_name, ModuleState.GENERATING)
            generation_store[session_id] = result.model_copy(deep=True)

            try:
                raw = await self._generate_module(module_name, prd, context, completed)
                save_module_files(result, module_name, _filter_valid_files(raw))
                if module_name == "frontend_core":
                    await self._run_frontend_qa(result, prd)
                completed.append(self._find_module(result, module_name))
            except Exception as exc:
                logger.error("Module %s failed: %s", module_name, exc)
                mark_module_failed(result, module_name, str(exc))

            generation_store[session_id] = result.model_copy(deep=True)

        self._apply_fixed_files(result, prd)

        set_module_state(result, _STRUCTURE_MODULE, ModuleState.GENERATING)
        generation_store[session_id] = result.model_copy(deep=True)
        try:
            module_status = await self._generate_project_structure_module(result, prd)
            self._apply_module_status(result, module_status)
        except Exception as exc:
            logger.error("Module %s failed: %s", _STRUCTURE_MODULE, exc)
            mark_module_failed(result, _STRUCTURE_MODULE, str(exc))

        generation_store[session_id] = result.model_copy(deep=True)
        finalize_result(result)
        generation_store[session_id] = result.model_copy(deep=True)
        return result

    async def _run_frontend_qa(self, result: GenerationResult, prd: PRDDocument) -> None:
        """QA only the structurally important files: App and page components.

        Utility components (StatusBadge, SkeletonLoader, etc.) are small and
        predictable — QA-ing them adds minutes without meaningful gain.
        """
        for module in result.modules:
            if module.module_name != "frontend_core":
                continue

            qa_targets = []
            passthrough = []
            for file in module.files:
                # App.jsx is a router/layout — it correctly has no loading or empty states.
                # Utility components (StatusBadge, Skeleton…) are small and predictable.
                # Only data-fetching page components benefit from QA.
                is_page = "/pages/" in file.path or file.path.endswith("Page.jsx") or file.path.endswith("Page.tsx")
                if (
                    is_page
                    and file.path.endswith((".jsx", ".tsx"))
                    and len(file.content.strip()) > 200
                ):
                    qa_targets.append(file)
                else:
                    passthrough.append(file)

            logger.info(
                "QA: %d important files, %d skipped", len(qa_targets), len(passthrough)
            )

            # Run QA concurrently — Ollama serialises internally but asyncio
            # overhead is still reduced and responses stream as they finish.
            async def _qa_one(f: GeneratedFile) -> GeneratedFile:
                try:
                    return await self._qa_agent.process(f, prd, max_iterations=1)
                except Exception as exc:
                    logger.warning("QA SKIP %s: %s", f.path, exc)
                    return f

            improved = await asyncio.gather(*[_qa_one(f) for f in qa_targets])
            module.files = list(improved) + passthrough
            logger.info("QA complete: %d files processed", len(improved))
            break

    @staticmethod
    def _apply_module_status(result: GenerationResult, module_status: ModuleStatus) -> None:
        for mod in result.modules:
            if mod.module_name == module_status.module_name:
                mod.files = module_status.files
                mod.status = module_status.status
                mod.error = module_status.error
                break
        result.total_files = sum(len(m.files) for m in result.modules)

    async def _generate_project_structure_module(
        self,
        result: GenerationResult,
        prd: PRDDocument,
    ) -> ModuleStatus:
        all_files: list[GeneratedFile] = []
        for module in result.modules:
            if module.module_name == _STRUCTURE_MODULE:
                continue
            for file in module.files:
                if file.content and len(file.content.strip()) > 0:
                    all_files.append(file)

        groups: dict[str, list[str]] = {}
        for file in all_files:
            folder = "/".join(file.path.split("/")[:-1]) or "root"
            groups.setdefault(folder, []).append(file.path.split("/")[-1])

        tree_lines = [f"# {prd.title}", ""]
        tree_lines.append("## Estructura del proyecto")
        tree_lines.append("```")
        for folder, files in sorted(groups.items()):
            tree_lines.append(f"{folder}/")
            for fname in sorted(files):
                tree_lines.append(f"  ├── {fname}")
        tree_lines.append("```")
        tree_lines.append("")

        tree_lines.append("## Resumen de generación")
        tree_lines.append("")
        for module in result.modules:
            if module.module_name == _STRUCTURE_MODULE:
                continue
            files_with_content = [
                f for f in module.files if f.content and len(f.content.strip()) > 0
            ]
            if not files_with_content:
                continue
            tree_lines.append(f"### {module.module_name}")
            for file in files_with_content:
                lines = len(file.content.split("\n"))
                tree_lines.append(f"  - `{file.path}` ({lines} líneas)")
            tree_lines.append("")

        total_files = len(all_files)
        total_lines = sum(len(f.content.split("\n")) for f in all_files)
        endpoints = list(prd.api_endpoints) if prd.api_endpoints else []

        tree_lines.append("## Estadísticas")
        tree_lines.append(f"- **Total archivos generados:** {total_files}")
        tree_lines.append(f"- **Total líneas de código:** {total_lines:,}")
        tree_lines.append(f"- **Endpoints API:** {len(endpoints)}")
        tree_lines.append(f"- **Entidades del modelo:** {len(prd.data_model)}")
        tree_lines.append(
            f"- **Stack:** {prd.proposed_stack.frontend} + {prd.proposed_stack.backend}"
        )
        tree_lines.append("")

        # Derive run commands from the PRD stack instead of hardcoding npm
        backend_stack = prd.proposed_stack.backend.lower()
        is_python_backend = any(
            kw in backend_stack
            for kw in ("python", "fastapi", "django", "flask", "uvicorn")
        )
        if is_python_backend:
            backend_install = "pip install -r requirements.txt"
            backend_run = "uvicorn main:app --reload"
        else:
            backend_install = "npm install"
            backend_run = "npm run seed && npm run dev"

        tree_lines.append("## Cómo correr el proyecto")
        tree_lines.append("```bash")
        tree_lines.append("# Backend")
        tree_lines.append(f"cd backend && {backend_install} && {backend_run}")
        tree_lines.append("")
        tree_lines.append("# Frontend")
        tree_lines.append("cd frontend && npm install && npm run dev")
        tree_lines.append("")
        tree_lines.append("# Con Docker")
        tree_lines.append("docker compose up --build")
        tree_lines.append("```")

        manifest_content = "\n".join(tree_lines)
        manifest_file = GeneratedFile(
            path="PROJECT_MANIFEST.md",
            content=manifest_content,
            module=_STRUCTURE_MODULE,
        )

        logger.info(
            "project_structure manifest: %d files, %d lines",
            total_files, total_lines,
        )

        return ModuleStatus(
            module_name=_STRUCTURE_MODULE,
            status=ModuleState.DONE,
            files=[manifest_file],
            error=None,
        )

    def _apply_fixed_files(self, result: GenerationResult, prd: PRDDocument) -> None:
        """Overwrite or inject canonical files that must not come from the LLM."""
        fixed = self._templates.get_fixed_files(prd)
        for path, content in fixed.items():
            existing: Optional[GeneratedFile] = None
            for module in result.modules:
                for file in module.files:
                    if file.path == path:
                        existing = file
                        break
                if existing:
                    break

            if existing:
                existing.content = content
                continue

            if path.startswith("frontend"):
                target_module = "frontend_core"
            elif path.startswith("backend"):
                target_module = "backend_core"
            elif path == "docker-compose.yml":
                target_module = "docker_compose"
            else:
                target_module = "dockerfile"
            for module in result.modules:
                if module.module_name == target_module:
                    module.files.append(
                        GeneratedFile(path=path, content=content, module=target_module)
                    )
                    break

        result.total_files = sum(len(m.files) for m in result.modules)
        logger.info("Applied %d fixed template files", len(fixed))

    async def _generate_module(
        self,
        module_name: str,
        prd: PRDDocument,
        context: ClarifyContext,
        completed: list[ModuleStatus],
    ) -> list[ModuleFileOutput]:
        if module_name in _TEMPLATE_MODULES:
            return await self._generate_template_module(module_name, prd, context, completed)
        if module_name == _SEED_MODULE:
            return await self._generate_seed_module(prd, context, completed)
        return await self._generate_files_one_by_one(module_name, prd, context, completed)

    async def _generate_seed_module(
        self,
        prd: PRDDocument,
        context: ClarifyContext,
        completed: list[ModuleStatus],
    ) -> list[ModuleFileOutput]:
        system = SystemMessage(content=build_module_prompt(_SEED_MODULE, prd, context))
        context_msgs = build_context_messages(completed)
        user = HumanMessage(
            content=(
                f"Generate seed data for '{prd.title}' ({context.app_type.value}). "
                "Entities: "
                + ", ".join(entity.name for entity in prd.data_model)
                + ". Return backend/src/config/seed.js and backend/src/config/init.sql."
            )
        )
        output = await self._llm.generate_files([system, *context_msgs, user])
        logger.info("seed module: %d files", len(output.files))
        return output.files

    def _planned_paths_for_module(
        self,
        module_name: str,
        prd: PRDDocument,
    ) -> list[str]:
        entities = prd.data_model
        use_ts = _is_typescript_stack(prd)
        ext = "tsx" if use_ts else "jsx"

        if module_name == "data_models":
            paths = ["backend/src/db/schema.sql", "backend/src/models/index.js"]
            for entity in entities:
                slug = entity.name.lower().replace(" ", "_")
                paths.append(f"backend/src/models/{slug}.js")
            return paths

        if module_name == "backend_core":
            paths = ["backend/src/server.js", "backend/src/app.js"]
            for entity in entities:
                slug = entity.name.lower().replace(" ", "_")
                paths.extend(
                    [
                        f"backend/src/routes/{slug}.js",
                        f"backend/src/services/{slug}Service.js",
                    ]
                )
            return paths

        if module_name == "frontend_core":
            paths = [
                f"frontend/src/App.{ext}",
                f"frontend/src/components/Layout.{ext}",
                f"frontend/src/components/Sidebar.{ext}",
                f"frontend/src/components/StatusBadge.{ext}",
                f"frontend/src/components/SkeletonLoader.{ext}",
                f"frontend/src/components/ErrorState.{ext}",
                f"frontend/src/components/EmptyState.{ext}",
            ]
            for entity in entities:
                name = entity.name.replace(" ", "")
                paths.append(f"frontend/src/pages/{name}Page.{ext}")
                paths.append(f"frontend/src/components/{name}Card.{ext}")
            return paths

        if module_name == "auth":
            return [
                "backend/src/middleware/auth.js",
                "backend/src/routes/auth.js",
                "backend/src/services/authService.js",
            ]

        return []

    async def _generate_files_one_by_one(
        self,
        module_name: str,
        prd: PRDDocument,
        context: ClarifyContext,
        completed: list[ModuleStatus],
    ) -> list[ModuleFileOutput]:
        paths = self._planned_paths_for_module(module_name, prd)
        if not paths:
            logger.warning("No planned paths for %s, skipping.", module_name)
            return []

        context_str = self._context_summary(completed)
        module_kb = self._kb.get_context_for_module(module_name, prd)
        if module_kb:
            context_str = f"{module_kb}\n\n{context_str}"
        logger.info("Generating %d files for %s (parallel)", len(paths), module_name)

        async def _gen(path: str) -> ModuleFileOutput | None:
            try:
                content = await self._generate_single_file(path, context_str, prd)
                return ModuleFileOutput(path=path, content=content) if content.strip() else None
            except Exception as exc:
                logger.warning("Failed to generate %s: %s", path, exc)
                return None

        results = await asyncio.gather(*[_gen(p) for p in paths])
        return [r for r in results if r is not None]

    async def _generate_single_file(
        self,
        file_path: str,
        context: str,
        prd: PRDDocument,
    ) -> str:
        kb_context = self._kb.get_context_for_file(file_path, prd)
        if kb_context:
            context = f"{kb_context}\n\n{context}"

        if file_path.startswith("frontend/src/"):
            llm = frontend_llm
        else:
            llm = code_llm

        ext = file_path.split(".")[-1] if "." in file_path else "txt"
        lang_map = {
            "jsx": "React JSX with Tailwind CSS",
            "tsx": "React TSX with Tailwind CSS",
            "js": "JavaScript",
            "ts": "TypeScript",
            "py": "Python",
            "sql": "SQL",
            "json": "JSON",
            "yml": "YAML",
            "yaml": "YAML",
            "md": "Markdown",
        }
        lang = lang_map.get(ext, ext)

        if ext in ("jsx", "tsx"):
            parts = file_path.split("/")
            entity_name = (
                parts[-1]
                .replace("Page.jsx", "")
                .replace("Page.tsx", "")
                .replace(".jsx", "")
                .replace(".tsx", "")
            )
            api_slug = f"{entity_name.lower()}s" if entity_name.lower() != "app" else "items"
            prompt = f"""You are a senior UI/UX frontend engineer.
Generate the complete React component for: {file_path}

Project: {prd.title}
Description: {prd.overview}
Entities: {[e.name for e in prd.data_model]}

MANDATORY UI REQUIREMENTS:
1. Full sidebar layout if this is App.{ext}:
   - Left sidebar (w-64) with nav links per entity + emoji icons
   - Active link: left border accent + background tint
   - App title at top of sidebar
   - Main content area flex-1 with proper padding

2. For page components (pages/*.{ext}):
   - Page header: title + subtitle + "Nuevo [entity]" button
   - Stats row: 3-4 metric cards showing counts/totals
   - Main content: card grid (grid-cols-1 md:grid-cols-2 lg:grid-cols-3)
     OR data table with sticky header
   - Loading skeleton: animate-pulse gray blocks
   - Empty state: centered icon + message + CTA button
   - Create/Edit modal with proper form fields

3. For card components (components/*.{ext}):
   - Clear hierarchy: title > badge > metadata > actions
   - Status badge: pill with semantic bg color
   - Hover effect: hover:shadow-lg hover:-translate-y-1 transition-all duration-200
   - Action buttons: edit (pencil icon) + delete (trash icon) as text

4. Fetch pattern — use this exactly:
   const [items, setItems] = useState([])
   const [loading, setLoading] = useState(true)
   const [error, setError] = useState(null)
   useEffect(() => {{
     fetch('/api/{api_slug}')
       .then(r => r.json())
       .then(setItems)
       .catch(e => setError(e.message))
       .finally(() => setLoading(false))
   }}, [])

5. Tailwind only — no external UI libraries, no inline styles
6. Complete code — no TODOs, no placeholders, no '// add logic here'

Context from other modules:
{context[:800]}

Generate {file_path} now — complete file, no truncation:"""
        else:
            prompt = f"""Generate complete {lang} code for: {file_path}
Project: {prd.title}
Stack: {prd.proposed_stack}
Context: {context[:600]}
Rules: no TODOs, no placeholders, production-ready code.
Generate {file_path}:"""

        response = await llm.ainvoke(prompt)
        content = response.content if isinstance(response.content, str) else str(response.content)
        content = content.strip()

        if content.startswith("```"):
            lines = content.split("\n")
            content = "\n".join(lines[1:])
            if content.endswith("```"):
                content = content[:-3].strip()

        model_name = getattr(llm, "model", "unknown")
        logger.info("[%s] %s: %d chars", model_name, file_path, len(content))
        return content

    @staticmethod
    def _strip_markdown(text: str) -> str:
        cleaned = text.strip()
        fence = re.search(r"^```[\w]*\n([\s\S]*?)```$", cleaned)
        return fence.group(1).strip() if fence else cleaned

    @staticmethod
    def _context_summary(completed: list[ModuleStatus]) -> str:
        """Build context string from all completed modules (up to 20 files each)."""
        parts: list[str] = []
        for mod in completed:
            for file in mod.files[:20]:
                parts.append(f"--- {file.path} ---\n{file.content[:2000]}")
        return "\n\n".join(parts) if parts else "(no prior files)"

    async def _generate_template_module(
        self,
        module_name: str,
        prd: PRDDocument,
        context: ClarifyContext,
        completed: list[ModuleStatus],
    ) -> list[ModuleFileOutput]:
        system = SystemMessage(content=build_module_prompt(module_name, prd, context))
        context_msgs = build_context_messages(completed)
        user = HumanMessage(
            content=f"Provide template parameters for '{module_name}' as structured JSON."
        )
        messages = [system, *context_msgs, user]
        stack = prd.proposed_stack
        slug = prd.title.lower().replace(" ", "-")[:30]

        if module_name == "dockerfile":
            try:
                params = await self._llm.generate_structured(messages, DockerfileParams)
            except Exception:
                params = self._templates.default_dockerfile_params(stack.backend)
            return [ModuleFileOutput(path="Dockerfile", content=self._templates.render_dockerfile(params))]

        if module_name == "docker_compose":
            try:
                params = await self._llm.generate_structured(messages, DockerComposeParams)
            except Exception:
                params = self._templates.default_compose_params(slug, stack.backend, stack.database)
            compose = self._templates.render_docker_compose(params)
            env = self._templates.render_env_example(
                EnvExampleParams(variables=["DATABASE_URL", "SECRET_KEY", "API_KEY"])
            )
            return [
                ModuleFileOutput(path="docker-compose.yml", content=compose),
                ModuleFileOutput(path=".env.example", content=env),
            ]

        params = await self._llm.generate_structured(messages, ReadmeParams, use_text_model=True)
        return [ModuleFileOutput(path="README.md", content=self._templates.render_readme(params))]

    @staticmethod
    def _find_module(result: GenerationResult, name: str) -> ModuleStatus:
        for mod in result.modules:
            if mod.module_name == name:
                return mod
        raise KeyError(f"Module {name} not found")


def collect_files_for_zip(session_id: str) -> list[GeneratedFile]:
    result = generation_store.get(session_id)
    if result is None:
        return []
    return all_generated_files(result)
