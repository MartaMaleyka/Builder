"""System prompts for modular code generation."""

from agents.template_manager import DEFAULT_DOCKER_COMPOSE
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
  - Dates between January 2024 and today

SEED DATA RULES:
- Project names: real business names like 'Rediseño Portal Clientes',
  'Migración Base de Datos Q1', 'App Móvil v2.0'
- User names: real Latin American names
- Descriptions: 1-2 sentences of real business context
- Dates: spread across last 6 months
- Statuses: mix of all possible values (not all 'pending')
- Prices: realistic for the domain (not 9.99 for everything)
- At least 10 records per main entity
- NEVER use 'Test', 'Sample', 'Placeholder', 'Project A', 'Task 1'"""


FRONTEND_CORE_PROMPT = """You are a senior UI/UX engineer.
Generate production-quality React components with Tailwind CSS.

DESIGN PRINCIPLES (apply all of them):
- Visual hierarchy: size, weight, and spacing guide the eye naturally
- Breathing room: generous padding and whitespace, never cramped
- Meaningful grouping: related elements visually clustered
- Feedback states: every interactive element has hover, focus, active states
- Empty states: when list is empty show an icon + message, not blank space
- Loading states: show skeleton loaders, not blank space
- Error states: friendly message with retry option
- Micro-interactions: subtle transitions (transition-all duration-200)
- Typography scale: use text-xs through text-4xl intentionally
- Shadow depth: use shadow-sm for cards, shadow-md on hover

COMPONENT STRUCTURE RULES:
Each page component must have:
  1. A page header with title + subtitle + primary action button
  2. A stats/summary bar if the entity has countable data
  3. The main content area (table or card grid depending on data type)
  4. Empty state component when data is []
  5. Loading skeleton when fetching

Each card component must have:
  1. A clear visual hierarchy (title > metadata > actions)
  2. A status badge if the entity has a status field
  3. Hover effect: hover:shadow-md hover:-translate-y-0.5 transition-all
  4. Action buttons revealed on hover (opacity-0 group-hover:opacity-100)
  5. Consistent padding: p-5 or p-6

Each table must have:
  1. Sticky header with sorted column indicators
  2. Alternating row backgrounds (even:bg-gray-50)
  3. Row hover highlight (hover:bg-opacity-50 transition-colors)
  4. Action column on the right with icon buttons
  5. Pagination or "showing X of Y" counter

LAYOUT RULES:
- Main layout: sidebar (w-64) + content area (flex-1)
- Sidebar: navigation links with active state indicator
- Content: max-w-7xl mx-auto px-4 sm:px-6 lg:px-8
- Page padding: py-8
- Section gaps: space-y-6

NAVIGATION SIDEBAR must include:
  - App name/logo at top
  - Nav links for each main entity with an icon (use emoji as icon placeholder)
  - Active link: distinct left border + background tint
  - Bottom section: settings link

FORMS must have:
  - Floating labels or clear label above input
  - Input focus ring (focus:ring-2 focus:ring-offset-2)
  - Validation error message below field in red
  - Submit button full-width on mobile, auto on desktop
  - Cancel button as ghost/outline variant

STATUS BADGES: use pill badges with semantic classes:
  - pending/draft:    bg-yellow-100 text-yellow-800
  - active/done:      bg-green-100  text-green-800
  - cancelled/error:  bg-red-100    text-red-800
  - in_progress:      bg-blue-100   text-blue-800

FETCH pattern — always use this hook pattern, never axios:
  const [data, setData] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetch('/api/{entity}')
      .then(r => { if (!r.ok) throw new Error(r.statusText); return r.json() })
      .then(d => setData(d))
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <SkeletonLoader />
  if (error) return <ErrorState message={error} onRetry={() => ...} />

SKELETON LOADER pattern:
  <div className="animate-pulse space-y-3">
    {[...Array(5)].map((_, i) => (
      <div key={i} className="h-16 bg-gray-200 rounded-lg" />
    ))}
  </div>

MODAL pattern for create/edit forms:
  - Fixed overlay: fixed inset-0 bg-black bg-opacity-50 z-50
  - Centered panel: max-w-lg w-full mx-auto mt-20 bg-white rounded-xl p-6
  - Close on overlay click and ESC key
  - Trap focus inside modal

APP.JSX must implement:
  - Sidebar layout wrapping all routes
  - Route per main entity page
  - 404 fallback route

Generate one file per component. Each file self-contained.
DO NOT use axios. DO NOT hardcode colors outside of Tailwind classes.
DO NOT use external UI libraries.
Generate complete, working code — no TODOs, no placeholders."""


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
        "frontend_core": base + FRONTEND_CORE_PROMPT,
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
        "data_models",
        "seed",
        "backend_core",
    ]
    if should_include_frontend(context):
        modules.append("frontend_core")
    if should_include_auth(prd):
        modules.append("auth")
    modules.extend(["dockerfile", "docker_compose", "readme", "project_structure"])
    return modules
