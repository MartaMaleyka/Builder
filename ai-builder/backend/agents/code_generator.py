"""Code Generator: produces a full project from an approved PRD."""

from __future__ import annotations

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
from agents.code_llm import CodeLLMClient
from agents.code_prompts import build_module_prompt, module_plan
from agents.template_manager import TemplateManager
from models.schemas import (
    ClarifyContext,
    DockerfileParams,
    DockerComposeParams,
    EnvExampleParams,
    GeneratedFile,
    GenerationResult,
    ModuleFileOutput,
    ModuleLLMOutput,
    ModuleState,
    ModuleStatus,
    PRDDocument,
    ReadmeParams,
)

generation_store: dict[str, GenerationResult] = {}

_TEMPLATE_MODULES = frozenset({"dockerfile", "docker_compose", "readme"})
_STRUCTURE_MODULE = "project_structure"
_MODULE_HINTS: dict[str, tuple[str, ...]] = {
    "data_models": ("model", "schema", "entity", "migration", "prisma", "/db/", "database"),
    "backend_core": ("route", "controller", "service", "handler", "router", "/api/", "backend/", "server"),
    "frontend_core": ("frontend/", "component", "page", "view", "/ui/", "layout", "styles", "astro", "react"),
    "auth": ("auth", "middleware", "guard", "login", "session", "jwt"),
}


def _filter_valid_files(files: list[ModuleFileOutput]) -> list[ModuleFileOutput]:
    """Skip directory entries and files with no content."""
    valid: list[ModuleFileOutput] = []
    for file in files:
        if file.path.endswith("/") or file.content.strip() == "":
            continue
        valid.append(file)
    return valid


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
        self._structure_paths: list[str] = []
        self._assigned_paths: set[str] = set()

    async def generate(self, session_id: str) -> GenerationResult:
        prd = self._get_prd(session_id)
        context = self._get_context(session_id)
        if prd is None:
            raise ValueError(f"No approved PRD for session {session_id}")
        if context is None:
            raise ValueError(f"No clarify context for session {session_id}")

        self._structure_paths = []
        self._assigned_paths = set()

        names = module_plan(prd, context)
        result = init_generation_result(session_id, names)
        generation_store[session_id] = result.model_copy(deep=True)

        completed: list[ModuleStatus] = []
        for module_name in names:
            set_module_state(result, module_name, ModuleState.GENERATING)
            generation_store[session_id] = result.model_copy(deep=True)

            try:
                raw = await self._generate_module(module_name, prd, context, completed)
                save_module_files(result, module_name, _filter_valid_files(raw))
                completed.append(self._find_module(result, module_name))
            except Exception as exc:
                print(f"[CodeGenerator] Module {module_name} failed: {exc}")
                mark_module_failed(result, module_name, str(exc))

            generation_store[session_id] = result.model_copy(deep=True)

        finalize_result(result)
        generation_store[session_id] = result.model_copy(deep=True)
        return result

    async def _generate_module(
        self,
        module_name: str,
        prd: PRDDocument,
        context: ClarifyContext,
        completed: list[ModuleStatus],
    ) -> list[ModuleFileOutput]:
        if module_name in _TEMPLATE_MODULES:
            return await self._generate_template_module(module_name, prd, context, completed)
        if module_name == _STRUCTURE_MODULE:
            return await self._generate_structure_module(prd, context, completed)
        return await self._generate_files_one_by_one(module_name, prd, completed)

    async def _generate_structure_module(
        self,
        prd: PRDDocument,
        context: ClarifyContext,
        completed: list[ModuleStatus],
    ) -> list[ModuleFileOutput]:
        system = SystemMessage(content=build_module_prompt(_STRUCTURE_MODULE, prd, context))
        context_msgs = build_context_messages(completed)
        user = HumanMessage(
            content="List every file path in the project tree. Return paths only; content may be empty."
        )
        output = await self._llm.generate_files([system, *context_msgs, user])
        raw = output.model_dump_json()
        print("=== PROJECT STRUCTURE RAW ===")
        print(repr(raw[:1000]))
        print("=== FIN RAW ===")
        self._structure_paths = self._extract_structure_paths(output)
        return output.files

    def _extract_structure_paths(self, output: ModuleLLMOutput) -> list[str]:
        paths: list[str] = []
        for f in output.files:
            if "." in f.path.split("/")[-1]:
                paths.append(f.path)
        print(f"[CodeGenerator] project_structure paths: {len(paths)}")
        for p in paths:
            print(f"  → {p}")
        return paths

    async def _generate_files_one_by_one(
        self,
        module_name: str,
        prd: PRDDocument,
        completed: list[ModuleStatus],
    ) -> list[ModuleFileOutput]:
        paths = self._paths_for_module(module_name)
        if not paths:
            print(f"[CodeGenerator] No structure paths for {module_name}, skipping.")
            return []

        context_str = self._context_summary(completed)
        files: list[ModuleFileOutput] = []
        for path in paths:
            print(f"[CodeGenerator] Generating {path} ({module_name})")
            content = await self._generate_single_file(path, context_str, prd)
            if content.strip():
                files.append(ModuleFileOutput(path=path, content=content))
                self._assigned_paths.add(path)
        return files

    def _paths_for_module(self, module_name: str) -> list[str]:
        hints = _MODULE_HINTS.get(module_name, ())
        matched: list[str] = []
        for path in self._structure_paths:
            if path in self._assigned_paths:
                continue
            lower = path.lower()
            if any(hint in lower for hint in hints):
                matched.append(path)
        return matched

    async def _generate_single_file(
        self,
        file_path: str,
        context: str,
        prd: PRDDocument,
    ) -> str:
        ext = file_path.split(".")[-1] if "." in file_path else "txt"
        lang_map = {
            "js": "JavaScript",
            "ts": "TypeScript",
            "jsx": "React JSX",
            "tsx": "React TSX",
            "py": "Python",
            "sql": "SQL",
            "json": "JSON",
            "yml": "YAML",
            "yaml": "YAML",
            "md": "Markdown",
            "env": "env file",
            "sh": "bash",
        }
        lang = lang_map.get(ext, ext)

        prompt = f"""Write the complete content for this file: {file_path}
Language: {lang}
Project: {prd.title}
Stack: frontend={prd.proposed_stack.frontend} backend={prd.proposed_stack.backend} database={prd.proposed_stack.database}

Project context:
{context[:800]}

Rules:
- Return ONLY the file content, no explanations
- No markdown code blocks, no backticks
- Must be complete and functional code
- No TODOs, no placeholders, no comments like 'add logic here'
- For package.json include real dependency versions
- For SQL include CREATE TABLE statements
- For server.js include actual Express routes

Write {file_path} now:"""

        from langchain_ollama import ChatOllama

        llm = ChatOllama(
            model="qwen2.5-coder:7b",
            base_url="http://localhost:11434",
            temperature=0.1,
            num_predict=2048,
        )
        response = await llm.ainvoke(prompt)
        raw = response.content if isinstance(response.content, str) else str(response.content)
        print(f"=== GENERATING {file_path} ===")
        print(f"=== RESPONSE LENGTH: {len(raw)} ===")
        print(f"=== FIRST 200 CHARS: {repr(raw[:200])} ===")
        content = raw.strip()

        if content.startswith("```"):
            lines = content.split("\n")
            content = "\n".join(lines[1:-1]) if lines[-1] == "```" else "\n".join(lines[1:])

        print(f"[SingleFile] {file_path}: {len(content)} chars")
        return content

    @staticmethod
    def _strip_markdown(text: str) -> str:
        cleaned = text.strip()
        fence = re.search(r"^```[\w]*\n([\s\S]*?)```$", cleaned)
        return fence.group(1).strip() if fence else cleaned

    @staticmethod
    def _context_summary(completed: list[ModuleStatus]) -> str:
        parts: list[str] = []
        for mod in completed:
            for file in mod.files[:10]:
                parts.append(f"--- {file.path} ---\n{file.content[:1500]}")
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
