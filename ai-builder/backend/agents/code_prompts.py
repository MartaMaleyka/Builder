"""System prompts for modular code generation."""

from agents.template_manager import DEFAULT_DOCKER_COMPOSE, TemplateManager
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
        f"  - {e.name}: {', '.join(f'{fld.name}:{fld.type}' for fld in e.fields)}"
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


PROJECT_STRUCTURE_PROMPT = """Generate a production-ready file list.

ARCHITECTURE: Clean layered architecture
- backend/src/config/       database, env, server config, seed.js, init.sql
- backend/src/models/       data models / ORM schemas
- backend/src/repositories/ database queries (1 per entity)
- backend/src/services/     business logic (1 per entity)
- backend/src/controllers/  request/response handling (1 per entity)
- backend/src/routes/       route definitions (1 per entity)
- backend/src/middleware/   auth, error handler, validator
- backend/src/utils/        helpers, constants, formatters
- backend/src/app.js        express app setup
- backend/src/server.js     entry point
- backend/package.json
- backend/Dockerfile
- backend/.env.example

- frontend/src/components/  reusable UI components
- frontend/src/pages/       one file per route/view
- frontend/src/hooks/       custom React hooks
- frontend/src/services/    API calls (1 per entity)
- frontend/src/context/     global state if needed
- frontend/src/utils/       helpers
- frontend/src/App.jsx
- frontend/src/main.jsx
- frontend/package.json
- frontend/Dockerfile
- frontend/vite.config.js
- frontend/tailwind.config.js
- frontend/postcss.config.js
- frontend/index.html

- docker-compose.yml
- README.md
- .env.example

frontend/package.json MUST have exactly this structure:
  scripts: { dev: "vite", build: "vite build", preview: "vite preview" }
  devDependencies: { vite: "^5.0.0", @vitejs/plugin-react: "^4.0.0",
    postcss: "^8.4.0", autoprefixer: "^10.4.0", tailwindcss: "^3.4.0" }
  dependencies: { react: "^18.2.0", react-dom: "^18.2.0" }
  NO astro, NO axios (use native fetch)

CRITICAL RULES:
- List ONLY files with extensions (.js, .py, .json, .sql, .md, .yml, etc)
- NO directory entries without extensions
- content must be empty string "" for all files (content is generated later)
- Adapt paths to the PRD stack (e.g. main.py for FastAPI instead of server.js)
- One repository, service, controller, and routes file per PRD entity

Generate between 25 and 40 files. ONLY files with extensions.
Return ONLY the JSON, no explanations."""


SEED_PROMPT = """You are generating realistic seed data for a
{app_type} application called "{title}".

Generate TWO files:

FILE 1: backend/src/config/seed.js
A Node.js script that:
- Connects to the database (use the same DB config as the project)
- Drops and recreates all tables (CREATE TABLE IF NOT EXISTS)
- Inserts realistic sample data: minimum 10 records per main entity
- Uses real-looking data (real names, real prices, real descriptions)
  NOT placeholder data like "Product 1", "User 1"
- Logs progress: console.log('Seeding products...') etc
- Can be run with: node src/config/seed.js
- Exports a runSeed() function AND runs it if called directly:
    if (require.main === module) runSeed()

FILE 2: backend/src/config/init.sql
Pure SQL file with:
- DROP TABLE IF EXISTS for each entity (in reverse dependency order)
- CREATE TABLE for each entity with:
    * Proper data types (VARCHAR, INTEGER, DECIMAL, TIMESTAMP, BOOLEAN)
    * Primary keys with AUTO INCREMENT or SERIAL
    * Foreign keys with ON DELETE CASCADE where appropriate
    * NOT NULL constraints on required fields
    * DEFAULT values where sensible (created_at DEFAULT NOW())
    * Indexes on foreign keys and frequently queried fields
- INSERT statements with 10+ realistic records per table
- Comments explaining each table

Data context:
  Entities: {entities}
  App description: {description}

Rules:
- Data must be in Spanish if the app is in Spanish
- Prices/amounts must be realistic for the domain
- Dates must be recent (2024-2025)
- No lorem ipsum, no "test data", no "sample"
- If the app has users, include varied roles
- If the app has products, include varied categories and prices

For inventory apps expect:
  - 4 categories: Electrónica, Ropa, Hogar, Deportes
  - 15 products with real name, description, price and stock
  - 3 users with different roles
  - 10 recent inventory movements
  - Dates between January 2024 and today"""


def build_seed_prompt(prd: PRDDocument, context: ClarifyContext) -> str:
    """Build the seed module prompt with PRD-specific context."""
    entities = ", ".join(entity.name for entity in prd.data_model) or "none"
    return (
        SEED_PROMPT.format(
            app_type=context.app_type.value,
            title=prd.title,
            entities=entities,
            description=prd.overview[:800],
        )
        + "\n\n"
        + _prd_summary(prd)
        + "\n\nReturn exactly these paths: backend/src/config/seed.js, "
        "backend/src/config/init.sql"
    )


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
        "seed": build_seed_prompt(prd, context),
        "backend_core": base + (
            "Module: backend_core\n"
            "Generate routes, controllers, services, and API layer.\n"
            "Implement ALL endpoints from the PRD with real business logic.\n"
            "Import and use the data models from the previous data_models module.\n"
            "Generate repository pattern: each entity has its own\n"
            "repository.js with raw SQL or ORM queries, service.js with\n"
            "business logic calling the repository, controller.js handling\n"
            "HTTP, and routes.js registering Express routes.\n"
            "Include proper error handling with try/catch in every function.\n"
            "Return structured JSON errors: { error: true, message: string, code: string }"
        ),
        "frontend_core": base + (
            "Module: frontend_core\n"
            "Generate the frontend application: pages, components, API client, routing.\n"
            "Use the frontend framework from the PRD stack.\n"
            "Wire UI to the backend endpoints defined in the PRD.\n"
            "Generate one page component per main view.\n"
            "Each page imports smaller reusable components.\n"
            "Use custom hooks for data fetching (useProducts, useOrders, etc).\n"
            "Each hook handles: loading state, error state, data state.\n"
            "Use fetch with async/await, never axios unless it's in package.json.\n"
            "Use React 18 createRoot API, never ReactDOM.render.\n"
            "For frontend/tailwind.config.js use Tailwind v3 syntax (content, not purge):\n"
            f"{TemplateManager.get_boilerplate_file('frontend/tailwind.config.js')}\n"
            "For frontend/src/main.jsx use React 18 createRoot:\n"
            f"{TemplateManager.get_boilerplate_file('frontend/src/main.jsx')}\n"
            "For frontend/package.json use React 18 + Vite scripts:\n"
            f"{TemplateManager.get_boilerplate_file('frontend/package.json')}"
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
            "Generate TWO Dockerfiles: backend/Dockerfile and frontend/Dockerfile.\n"
            "Each service builds from its own context directory.\n"
            "Multi-stage build if appropriate. Non-root user when possible."
        ),
        "docker_compose": base + (
            "Module: docker_compose\n"
            "Return docker-compose.yml with separate backend and frontend services.\n"
            "Each service builds from its own Dockerfile (./backend and ./frontend).\n"
            "No postgres — backend uses SQLite.\n"
            "Use this exact structure:\n"
            f"{DEFAULT_DOCKER_COMPOSE}"
        ),
        "readme": base + (
            "Module: readme\n"
            "Return README.md with setup, env vars, run commands, and API overview.\n"
            "Clear step-by-step instructions for local development.\n"
            "ALWAYS include this section verbatim:\n\n"
            "## Datos de prueba\n"
            "Para cargar datos de ejemplo:\n"
            "```bash\n"
            "cd backend\n"
            "npm run seed\n"
            "```\n"
            "Esto crea las tablas y carga datos realistas de ejemplo."
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
        "seed",
        "backend_core",
    ]
    if should_include_frontend(context):
        modules.append("frontend_core")
    if should_include_auth(prd):
        modules.append("auth")
    modules.extend(["dockerfile", "docker_compose", "readme"])
    return modules
