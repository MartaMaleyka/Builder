# Builder

AI Builder — genera PRDs y código a partir de conversaciones con agentes LLM (Ollama).

## Estructura

- `ai-builder/backend/` — API FastAPI + agentes
- `ai-builder/frontend/` — UI React + Vite + Tailwind

## Setup

### Backend

```bash
cd ai-builder/backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn api.main:app --reload
```

### Frontend

```bash
cd ai-builder/frontend
npm install
npm run dev
```
