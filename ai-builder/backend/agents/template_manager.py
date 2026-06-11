"""Jinja2 template rendering for infrastructure and docs files."""

from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

from models.schemas import (
    DockerfileParams,
    DockerComposeParams,
    EnvExampleParams,
    PRDDocument,
    ReadmeParams,
)

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"

FIXED_FILES: dict[str, str] = {
    "frontend/package.json": """{
  "name": "{project_slug}",
  "version": "1.0.0",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.8.0"
  },
  "devDependencies": {
    "vite": "^5.0.0",
    "@vitejs/plugin-react": "^4.0.0",
    "tailwindcss": "^3.4.0",
    "postcss": "^8.4.0",
    "autoprefixer": "^10.4.0"
  }
}""",
    "frontend/vite.config.js": """import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://localhost:3001'
    }
  }
})""",
    "frontend/tailwind.config.js": """/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: { extend: {} },
  plugins: [],
}""",
    "frontend/postcss.config.js": """export default {
  plugins: { tailwindcss: {}, autoprefixer: {} }
}""",
    "frontend/index.html": """<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{project_title}</title>
</head>
<body>
  <div id="root"></div>
  <script type="module" src="/src/main.jsx"></script>
</body>
</html>""",
    "frontend/src/index.css": """@tailwind base;
@tailwind components;
@tailwind utilities;

* { box-sizing: border-box; }
body {
  font-family: Inter, system-ui, -apple-system, sans-serif;
  background: #f9fafb;
  color: #111827;
}""",
    "frontend/src/main.jsx": """import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import './index.css'
import App from './App.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>
)""",
    "frontend/Dockerfile": """FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

FROM node:20-alpine
WORKDIR /app
RUN npm install -g serve
COPY --from=builder /app/dist ./dist
EXPOSE 3000
CMD ["serve", "-s", "dist", "-l", "3000"]""",
    "backend/package.json": """{
  "name": "{project_slug}-backend",
  "version": "1.0.0",
  "type": "commonjs",
  "scripts": {
    "start": "node src/server.js",
    "dev": "nodemon src/server.js",
    "seed": "node src/config/seed.js",
    "seed:fresh": "node src/config/seed.js --fresh"
  },
  "dependencies": {
    "express": "^4.18.0",
    "better-sqlite3": "^9.0.0",
    "cors": "^2.8.5",
    "dotenv": "^16.0.0"
  },
  "devDependencies": {
    "nodemon": "^3.0.0"
  }
}""",
    "backend/Dockerfile": """FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install --production
COPY . .
EXPOSE 3001
CMD ["node", "src/server.js"]""",
    "docker-compose.yml": """services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "3001:3001"
    environment:
      PORT: "3001"
      NODE_ENV: production
    restart: unless-stopped

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    depends_on:
      - backend
    environment:
      VITE_API_URL: http://localhost:3001
    restart: unless-stopped""",
}

DEFAULT_DOCKER_COMPOSE = FIXED_FILES["docker-compose.yml"]


class TemplateManager:
    """Renders project boilerplate files from Jinja2 templates."""

    def __init__(self) -> None:
        self._env = Environment(
            loader=FileSystemLoader(str(_TEMPLATES_DIR)),
            autoescape=select_autoescape(enabled_extensions=()),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def get_fixed_files(self, prd: PRDDocument) -> dict[str, str]:
        """Return canonical file contents that must never be LLM-generated."""
        slug = prd.title.lower().replace(" ", "-")
        title = prd.title
        rendered: dict[str, str] = {}
        for path, content in FIXED_FILES.items():
            rendered[path] = (
                content.replace("{project_slug}", slug).replace("{project_title}", title)
            )
        return rendered

    @staticmethod
    def get_boilerplate_file(path: str) -> Optional[str]:
        """Return raw boilerplate template for prompts (placeholders intact)."""
        return FIXED_FILES.get(path)

    def render_dockerfile(self, params: DockerfileParams) -> str:
        template = self._env.get_template("Dockerfile.j2")
        return template.render(
            base_image=params.base_image,
            port=params.port,
            start_command=params.start_command,
        )

    def render_docker_compose(self, params: Optional[DockerComposeParams] = None) -> str:
        return DEFAULT_DOCKER_COMPOSE

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
    def default_dockerfile_params(stack_backend: str, port: int = 3001) -> DockerfileParams:
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
        return DockerComposeParams(services=[])
