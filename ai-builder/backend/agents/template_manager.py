"""Jinja2 template rendering for infrastructure and docs files."""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from models.schemas import (
    ComposeServiceSpec,
    DockerfileParams,
    DockerComposeParams,
    EnvExampleParams,
    ReadmeParams,
)

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"


class TemplateManager:
    """Renders project boilerplate files from Jinja2 templates."""

    def __init__(self) -> None:
        self._env = Environment(
            loader=FileSystemLoader(str(_TEMPLATES_DIR)),
            autoescape=select_autoescape(enabled_extensions=()),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def render_dockerfile(self, params: DockerfileParams) -> str:
        template = self._env.get_template("Dockerfile.j2")
        return template.render(
            base_image=params.base_image,
            port=params.port,
            start_command=params.start_command,
        )

    def render_docker_compose(self, params: DockerComposeParams) -> str:
        template = self._env.get_template("docker-compose.j2")
        return template.render(services=params.services)

    def render_readme(self, params: ReadmeParams) -> str:
        template = self._env.get_template("readme.j2")
        return template.render(
            title=params.title,
            description=params.description,
            stack=params.stack,
            setup_steps=params.setup_steps,
        )

    def render_env_example(self, params: EnvExampleParams) -> str:
        template = self._env.get_template("env_example.j2")
        return template.render(variables=params.variables)

    @staticmethod
    def default_dockerfile_params(stack_backend: str, port: int = 8000) -> DockerfileParams:
        backend = stack_backend.lower()
        if "node" in backend or "express" in backend or "nestjs" in backend:
            return DockerfileParams(
                base_image="node:20-alpine",
                port=port,
                start_command='["npm", "start"]',
            )
        return DockerfileParams(
            base_image="python:3.11-slim",
            port=port,
            start_command='["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]',
        )

    @staticmethod
    def default_compose_params(
        project_name: str, stack_backend: str, database: str
    ) -> DockerComposeParams:
        services = [
            ComposeServiceSpec(
                name="app",
                image=f"{project_name}-app",
                ports=["8000:8000"],
                env_vars={"DATABASE_URL": "postgresql://user:pass@db:5432/app"},
            )
        ]
        if "postgres" in database.lower():
            services.append(
                ComposeServiceSpec(
                    name="db",
                    image="postgres:16-alpine",
                    ports=["5432:5432"],
                    env_vars={
                        "POSTGRES_USER": "user",
                        "POSTGRES_PASSWORD": "pass",
                        "POSTGRES_DB": "app",
                    },
                )
            )
        return DockerComposeParams(services=services)
