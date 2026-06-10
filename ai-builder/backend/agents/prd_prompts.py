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
- data_model: main entities with fields and relationships
- api_endpoints: include relevant REST endpoints if app_type is api, web_app, or complex_system;
  use empty list for cli or pure mobile_app without backend
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

Be specific and actionable. Do not invent major features beyond the context."""
