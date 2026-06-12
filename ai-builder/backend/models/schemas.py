"""Pydantic schemas for the AI Builder API."""

from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field


class AppType(str, Enum):
    """Supported application categories."""

    WEB_APP = "web_app"
    MOBILE_APP = "mobile_app"
    API = "api"
    CLI = "cli"
    COMPLEX_SYSTEM = "complex_system"


class ScaleExpectation(str, Enum):
    """Expected deployment scale."""

    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


class Priority(str, Enum):
    """Requirement priority level."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ClarifyContext(BaseModel):
    """Structured context emitted when clarification is complete."""

    app_type: AppType
    description: str
    core_features: list[str]
    tech_preferences: Optional[str] = None
    target_users: str
    scale_expectation: ScaleExpectation
    integrations: list[str] = Field(default_factory=list)


class ClarifyResponse(BaseModel):
    """Response returned by the Clarify Agent after each turn."""

    needs_more_info: bool
    questions: list[str] = Field(default_factory=list)
    context: Optional[ClarifyContext] = None


class ClarifyRequest(BaseModel):
    """Incoming payload for POST /clarify."""

    message: str
    session_id: str


class AgentLLMOutput(BaseModel):
    """Structured output parsed from the LLM."""

    needs_more_info: bool
    questions: list[str] = Field(default_factory=list)
    context: Optional[ClarifyContext] = None


class UserStory(BaseModel):
    """User story with acceptance criteria."""

    role: str
    action: str
    benefit: str
    acceptance_criteria: list[str]


class Requirement(BaseModel):
    """Functional or non-functional requirement."""

    id: str
    description: str
    priority: Priority


class ProposedStack(BaseModel):
    """Technology stack recommendation."""

    frontend: str
    backend: str
    database: str
    auth: str
    infra: str
    extras: list[str] = Field(default_factory=list)


class ArchitecturePattern(str, Enum):
    """Application architecture pattern."""

    MVC = "MVC"
    CLEAN_ARCHITECTURE = "Clean Architecture"
    LAYERED = "Layered"


class TechnicalSpec(BaseModel):
    """Technical specifications inferred for the project."""

    architecture_pattern: ArchitecturePattern
    folder_structure: str
    naming_conventions: str
    error_handling_strategy: str
    state_management: str


class FrontendComponent(BaseModel):
    """Frontend UI component specification."""

    name: str
    description: str
    props: list[str] = Field(default_factory=list)
    route: Optional[str] = None


class DatabaseField(BaseModel):
    """Database column with type and constraints."""

    name: str
    type: str
    constraints: list[str] = Field(default_factory=list)


class DataEntity(BaseModel):
    """Primary data entity in the system."""

    name: str
    fields: list[DatabaseField]
    relationships: list[str] = Field(default_factory=list)


class APIEndpoint(BaseModel):
    """REST API endpoint definition."""

    method: str
    path: str
    description: str
    auth_required: bool = False


class Milestone(BaseModel):
    """Delivery milestone phase."""

    phase: int
    name: str
    deliverables: list[str]
    estimated_weeks: int


class PRDDocument(BaseModel):
    """Product Requirements Document generated from clarified context."""

    title: str
    overview: str
    goals: list[str]
    out_of_scope: list[str]
    user_stories: list[UserStory]
    functional_requirements: list[Requirement]
    non_functional_requirements: list[Requirement]
    proposed_stack: ProposedStack
    technical_specifications: TechnicalSpec
    data_model: list[DataEntity]
    frontend_components: list[FrontendComponent] = Field(default_factory=list)
    api_endpoints: list[APIEndpoint] = Field(default_factory=list)
    milestones: list[Milestone]


class PRDGenerateRequest(BaseModel):
    """Incoming payload for POST /prd/generate."""

    session_id: str


class PRDApproveRequest(BaseModel):
    """Incoming payload for POST /prd/approve."""

    session_id: str
    approved: bool
    edited_prd: Optional[PRDDocument] = None


class PRDApproveResponse(BaseModel):
    """Response after PRD approval or rejection."""

    status: Literal["approved", "rejected"]
    prd: Optional[PRDDocument] = None


class ModuleState(str, Enum):
    """Status of an individual generation module."""

    PENDING = "pending"
    GENERATING = "generating"
    DONE = "done"
    FAILED = "failed"


class GenerationStatus(str, Enum):
    """Overall code generation status."""

    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    FAILED = "failed"


class GeneratedFile(BaseModel):
    """A single generated project file."""

    path: str
    content: str
    module: str


class ModuleStatus(BaseModel):
    """Generation status for one module."""

    module_name: str
    status: ModuleState
    files: list[GeneratedFile] = Field(default_factory=list)
    error: Optional[str] = None


class GenerationResult(BaseModel):
    """Full code generation result for a session."""

    session_id: str
    modules: list[ModuleStatus]
    total_files: int
    status: GenerationStatus


class CodeGenerateRequest(BaseModel):
    """Incoming payload for POST /code/generate."""

    session_id: str


class CodeGenerateStartResponse(BaseModel):
    """Immediate response when code generation is kicked off."""

    status: str
    session_id: str


class ModuleFileOutput(BaseModel):
    """Single file returned by the code LLM."""

    path: str
    content: str


class ModuleLLMOutput(BaseModel):
    """Structured LLM output for a code module."""

    files: list[ModuleFileOutput]


class ComposeServiceSpec(BaseModel):
    """Docker Compose service definition for templates."""

    name: str
    image: str
    ports: list[str] = Field(default_factory=list)
    env_vars: dict[str, str] = Field(default_factory=dict)


class DockerfileParams(BaseModel):
    """Parameters for the Dockerfile template."""

    base_image: str
    port: int
    start_command: str


class DockerComposeParams(BaseModel):
    """Parameters for the docker-compose template."""

    services: list[ComposeServiceSpec]


class ReadmeParams(BaseModel):
    """Parameters for the README template."""

    title: str
    description: str
    stack: str
    setup_steps: list[str]


class EnvExampleParams(BaseModel):
    """Parameters for the .env.example template."""

    variables: list[str]
