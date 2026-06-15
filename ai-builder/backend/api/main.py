"""FastAPI application for the AI Builder full pipeline."""

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from agents.clarify_agent import ClarifyAgent
from agents.code_generator import CodeGenerator, collect_files_for_zip, generation_store
from agents.code_zip import build_project_zip
from agents.prd_generator import PRDGenerator
from knowledge_base.kb_graph import KnowledgeGraph
from knowledge_base.kb_loader import init_knowledge_base
from models.schemas import (
    ClarifyContext,
    ClarifyRequest,
    ClarifyResponse,
    CodeGenerateRequest,
    CodeGenerateStartResponse,
    GenerationResult,
    GenerationStatus,
    PRDApproveRequest,
    PRDApproveResponse,
    PRDDocument,
    PRDGenerateRequest,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

SESSION_TTL_HOURS = 24

_sessions: dict[str, ClarifyAgent] = {}
_session_timestamps: dict[str, datetime] = {}
clarify_context_store: dict[str, ClarifyContext] = {}
prd_store: dict[str, PRDDocument] = {}
approved_prd_store: dict[str, PRDDocument] = {}
_prd_generator = PRDGenerator()
_code_generator = CodeGenerator(
    get_prd=approved_prd_store.get,
    get_context=clarify_context_store.get,
)
_generation_tasks: dict[str, asyncio.Task] = {}


async def _cleanup_old_sessions() -> None:
    """Remove sessions older than SESSION_TTL_HOURS every hour."""
    while True:
        await asyncio.sleep(3600)
        cutoff = datetime.utcnow() - timedelta(hours=SESSION_TTL_HOURS)
        expired = [sid for sid, ts in _session_timestamps.items() if ts < cutoff]
        for sid in expired:
            _sessions.pop(sid, None)
            clarify_context_store.pop(sid, None)
            prd_store.pop(sid, None)
            approved_prd_store.pop(sid, None)
            generation_store.pop(sid, None)
            _generation_tasks.pop(sid, None)
            _session_timestamps.pop(sid, None)
        if expired:
            logger.info("Cleaned up %d expired sessions", len(expired))


@asynccontextmanager
async def lifespan(app: FastAPI):
    graph = KnowledgeGraph()
    logger.info("[API] Graph: %d nodes", graph.graph.number_of_nodes())
    init_knowledge_base()
    logger.info("[API] Knowledge base ready")

    asyncio.create_task(_cleanup_old_sessions())
    yield


app = FastAPI(
    title="AI Software Architect Builder",
    description="Clarify, PRD, and Code Generation API.",
    version="0.3.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _get_or_create_agent(session_id: str) -> ClarifyAgent:
    if session_id not in _sessions:
        _sessions[session_id] = ClarifyAgent(session_id=session_id)
        logger.info("New session agent created: %s", session_id)
    _session_timestamps[session_id] = datetime.utcnow()
    return _sessions[session_id]


async def _run_generation(session_id: str) -> None:
    try:
        await _code_generator.generate(session_id)
    except Exception as exc:
        logger.error("Generation failed for %s: %s", session_id, exc)
        existing = generation_store.get(session_id)
        if existing is not None:
            existing.status = GenerationStatus.FAILED
            generation_store[session_id] = existing.model_copy(deep=True)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/clarify", response_model=ClarifyResponse)
def clarify(request: ClarifyRequest) -> ClarifyResponse:
    message = request.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="message must not be empty")
    session_id = request.session_id.strip()
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id must not be empty")

    agent = _get_or_create_agent(session_id)
    response = agent.chat(message)
    if not response.needs_more_info and response.context is not None:
        clarify_context_store[session_id] = response.context
    return response


@app.post("/prd/generate", response_model=PRDDocument)
async def generate_prd(request: PRDGenerateRequest) -> PRDDocument:
    session_id = request.session_id.strip()
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id must not be empty")

    context = clarify_context_store.get(session_id)
    if context is None:
        raise HTTPException(
            status_code=404,
            detail="No clarified context found for this session. Complete /clarify first.",
        )

    prd = await _prd_generator.generate(context)
    prd_store[session_id] = prd
    return prd


@app.post("/prd/approve", response_model=PRDApproveResponse)
def approve_prd(request: PRDApproveRequest) -> PRDApproveResponse:
    session_id = request.session_id.strip()
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id must not be empty")

    if not request.approved:
        return PRDApproveResponse(status="rejected")

    final_prd = request.edited_prd or prd_store.get(session_id)
    if final_prd is None:
        raise HTTPException(
            status_code=404,
            detail="No PRD found for this session. Generate one with /prd/generate first.",
        )

    approved_prd_store[session_id] = final_prd
    return PRDApproveResponse(status="approved", prd=final_prd)


@app.get("/prd/{session_id}", response_model=PRDDocument)
def get_prd(session_id: str) -> PRDDocument:
    sid = session_id.strip()
    if sid in approved_prd_store:
        return approved_prd_store[sid]
    if sid in prd_store:
        return prd_store[sid]
    raise HTTPException(status_code=404, detail="No PRD found for this session")


@app.post("/code/generate", response_model=CodeGenerateStartResponse)
async def start_code_generation(
    request: CodeGenerateRequest,
) -> CodeGenerateStartResponse:
    session_id = request.session_id.strip()
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id must not be empty")
    if session_id not in approved_prd_store:
        raise HTTPException(
            status_code=404,
            detail="No approved PRD for this session. Approve a PRD first.",
        )
    if session_id in _generation_tasks and not _generation_tasks[session_id].done():
        return CodeGenerateStartResponse(status="started", session_id=session_id)

    task = asyncio.create_task(_run_generation(session_id))
    _generation_tasks[session_id] = task
    return CodeGenerateStartResponse(status="started", session_id=session_id)


@app.get("/code/status/{session_id}", response_model=GenerationResult)
def code_status(session_id: str) -> GenerationResult:
    sid = session_id.strip()
    result = generation_store.get(sid)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail="No generation found for this session. Call /code/generate first.",
        )
    return result


@app.get("/code/download/{session_id}")
def code_download(session_id: str) -> Response:
    sid = session_id.strip()
    result = generation_store.get(sid)
    if result is None:
        raise HTTPException(status_code=404, detail="No generation found for this session.")
    if result.status != GenerationStatus.COMPLETE:
        raise HTTPException(
            status_code=409,
            detail=f"Generation not complete. Current status: {result.status.value}",
        )

    files = collect_files_for_zip(sid)
    if not files:
        raise HTTPException(status_code=404, detail="No generated files available.")

    archive = build_project_zip(files, archive_name=sid)
    filename = f"{sid}-project.zip"
    return Response(
        content=archive,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
