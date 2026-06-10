"""System prompts for modular code generation."""

from models.schemas import AppType, ClarifyContext, PRDDocument

_COMMON_RULES = """Rules for ALL generated code:
- Production-ready code only — no toy examples or stubs
- No TODO comments or placeholders like "add your logic here"
- Variable and function names in English
- Include basic error handling (try/except, HTTP error responses, validation)
- Use EXACTLY the stack defined in the PRD ProposedStack
- Return files as path + full file content
- Paths use forward slashes relative to project root
- Do not wrap output in markdown fences"""


def _prd_summary(prd: PRDDocument) -> str:
    stack = prd.proposed_stack
    endpoints = "\n".join(
        f"  {e.method} {e.path} — {e.description} (auth={e.auth_required})"
        for e in prd.api_endpoints
    ) or "  (none)"
    entities = "\n".join(
        f"  - {e.name}: {', '.join(e.fields)}"
        for e in prd.data_model
    )
    return f"""PRD: {prd.title}
Overview: {prd.overview[:500]}
Stack — frontend: {stack.frontend}, backend: {stack.backend},
  database: {stack.database}, auth: {stack.auth}, infra: {stack.infra}
API endpoints:
{endpoints}
Data model:
{entities}"""


PROJECT_STRUCTURE_PROMPT = """You are a senior software architect.
Generate the complete list of FILES (not folders) for this project.

CRITICAL RULES:
- List ONLY files with extensions (.js, .py, .json, .sql, .md, .yml, etc)
- NO directory entries without extensions
- Every file must have a realistic path like "backend/server.js"
- Include ALL files needed to run the project
- content must be empty string "" for all files (content is generated later)

Required files to include (adapt paths to the stack):
  backend/server.js (or main.py for FastAPI)
  backend/package.json (or requirements.txt for Python)
  backend/routes/[entity].js (one per main entity)
  backend/models/[entity].js (one per main entity)
  backend/config/db.config.js
  backend/.env.example
  frontend/package.json
  frontend/vite.config.js (if React+Vite)
  frontend/tailwind.config.js (if Tailwind)
  frontend/index.html
  frontend/src/main.jsx
  frontend/src/App.jsx
  frontend/src/components/[MainComponent].jsx (2-3 components)
  docker-compose.yml
  README.md

Generate between 12 and 20 files total.
Return ONLY the JSON, no explanations."""


def _context_line(context: ClarifyContext) -> str:
    return (
        f"app_type={context.app_type.value}, "
        f"scale={context.scale_expectation.value}, "
        f"users={context.target_users}"
    )


def build_module_prompt(
    module: str, prd: PRDDocument, context: ClarifyContext
) -> str:
    """Build the system prompt for a specific generation module."""
    base = f"{_COMMON_RULES}\n\n{_prd_summary(prd)}\n\nContext: {_context_line(context)}\n\n"
    prompts = {
        "project_structure": (
            PROJECT_STRUCTURE_PROMPT
            + "\n\n"
            + _prd_summary(prd)
            + "\n\nContext: "
            + _context_line(context)
        ),
        "data_models": base + (
            "Module: data_models\n"
            "Generate database schemas, ORM models, migrations, and DTOs.\n"
            "Match every entity in the PRD data_model with proper types and relations.\n"
            "Use the database technology from the PRD stack."
        ),
        "backend_core": base + (
            "Module: backend_core\n"
            "Generate routes, controllers, services, and API layer.\n"
            "Implement ALL endpoints from the PRD with real business logic.\n"
            "Import and use the data models from the previous data_models module."
        ),
        "frontend_core": base + (
            "Module: frontend_core\n"
            "Generate the frontend application: pages, components, API client, routing.\n"
            "Use the frontend framework from the PRD stack.\n"
            "Wire UI to the backend endpoints defined in the PRD."
        ),
        "auth": base + (
            "Module: auth\n"
            "Generate authentication and authorization: login, tokens/sessions, "
            "middleware/guards, and protected route patterns.\n"
            "Use the auth approach from the PRD stack.\n"
            "Cover every endpoint marked auth_required=True."
        ),
        "dockerfile": base + (
            "Module: dockerfile\n"
            "Return a single file path 'Dockerfile' with a production-ready Dockerfile.\n"
            "Multi-stage build if appropriate. Non-root user when possible."
        ),
        "docker_compose": base + (
            "Module: docker_compose\n"
            "Return docker-compose.yml with app + database + any required services.\n"
            "Include sensible env vars and volume mounts."
        ),
        "readme": base + (
            "Module: readme\n"
            "Return README.md with setup, env vars, run commands, and API overview.\n"
            "Clear step-by-step instructions for local development."
        ),
    }
    return prompts[module]


def should_include_frontend(context: ClarifyContext) -> bool:
    return context.app_type not in (AppType.API, AppType.CLI)


def should_include_auth(prd: PRDDocument) -> bool:
    return any(ep.auth_required for ep in prd.api_endpoints) or bool(
        prd.proposed_stack.auth.strip()
        and prd.proposed_stack.auth.lower() not in ("none", "n/a", "no auth")
    )


def module_plan(prd: PRDDocument, context: ClarifyContext) -> list[str]:
    """Return ordered module names to generate for this project."""
    modules = [
        "project_structure",
        "data_models",
        "backend_core",
    ]
    if should_include_frontend(context):
        modules.append("frontend_core")
    if should_include_auth(prd):
        modules.append("auth")
    modules.extend(["dockerfile", "docker_compose", "readme"])
    return modules
