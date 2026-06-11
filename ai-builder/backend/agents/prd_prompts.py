"""System prompts for PRD generation."""

from models.schemas import AppType, ClarifyContext


def _language_instruction(app_type: AppType) -> str:
    if app_type in (AppType.API, AppType.CLI, AppType.COMPLEX_SYSTEM):
        return "Write the entire PRD in English."
    return "Write the entire PRD in Spanish."


def build_prd_system_prompt(context: ClarifyContext) -> str:
    """Build the system prompt for PRD generation from clarified context."""
    lang = _language_instruction(context.app_type)
    tech = context.tech_preferences or "none specified — propose sensible defaults"
    integrations = ", ".join(context.integrations) if context.integrations else "none"
    features = "\n".join(f"- {f}" for f in context.core_features)

    return f"""You are a senior software architect. Generate a complete Product Requirements
Document (PRD) from the clarified project context below.

{lang}

Output must satisfy these constraints:
- overview: 2-3 paragraphs summarizing the product
- goals: 3-5 clear, measurable objectives
- out_of_scope: explicit list of what this version will NOT include
- user_stories: at least 5 stories; each with role, action, benefit, and acceptance_criteria
- functional_requirements: detailed FRs with unique ids (e.g. FR-001), priority high|medium|low
- non_functional_requirements: NFRs with unique ids (e.g. NFR-001), priority high|medium|low
- proposed_stack: recommend frontend, backend, database, auth, infra, and extras list
  CRÍTICO: El campo proposed_stack DEBE usar exactamente las tecnologías mencionadas
  en tech_preferences. Si el usuario dijo React + Astro + Tailwind, el frontend DEBE
  ser React + Astro + Tailwind, no React.js genérico. Si dijo Node.js, el backend DEBE
  ser Node.js + Express, no FastAPI. Nunca sustituir tecnologías por otras aunque te
  parezcan mejores. Si tech_preferences es null, entonces propones el stack más adecuado.
- technical_specifications: ALWAYS infer even if the user did not mention them:
    architecture_pattern: one of "MVC", "Clean Architecture", "Layered"
    folder_structure: proposed folder tree as a text description
    naming_conventions: e.g. snake_case backend, camelCase frontend, PascalCase components
    error_handling_strategy: how API and UI handle errors (HTTP codes, user messages, logging)
    state_management: how frontend state is managed (Context, Redux, local state, etc.)
- data_model: main entities; each field is a DatabaseField object with:
    name, type (SQL/ORM type), constraints (NOT NULL, UNIQUE, FK, INDEX, etc.)
  Include suggested indexes in constraints where appropriate.
- frontend_components: minimum 5 components for web/mobile apps; each with:
    name, description, props (list of prop names), route (path or null for layout-only)
  Skip or use empty list only for api/cli app_type without UI.
- api_endpoints: NEVER leave empty for api, web_app, or complex_system.
  For EACH DataEntity in data_model, generate at minimum these CRUD endpoints
  (use plural lowercase entity name in path):
    GET    /api/{{entity}}          — list with pagination
    GET    /api/{{entity}}/{{id}}   — detail
    POST   /api/{{entity}}          — create
    PUT    /api/{{entity}}/{{id}}   — update
    DELETE /api/{{entity}}/{{id}}   — delete
  Add business-specific endpoints beyond CRUD where the app requires them.
  Use empty list only for cli or pure mobile_app without backend.
- milestones: 3-4 phases with phase number, name, deliverables, estimated_weeks

Scale deliverables to {context.scale_expectation.value} scale expectations.

## Project context
- app_type: {context.app_type.value}
- description: {context.description}
- core_features:
{features}
- tech_preferences: {tech}
- target_users: {context.target_users}
- scale_expectation: {context.scale_expectation.value}
- integrations: {integrations}

Be specific and actionable. Do not invent major features beyond the context.
Infer technical_specifications, frontend_components, and full api_endpoints automatically."""
