"""JARVIS AI OS — FastAPI application entry point."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlalchemy import text
from fastapi.middleware.cors import CORSMiddleware
from .core.database import engine, async_session
from .core.seeder import seed_agents
from .models import Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create database tables on startup, seed defaults, dispose engine on shutdown."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # SQLite create_all does not evolve existing tables; these columns are additive.
        for statement in (
            "ALTER TABLE memories ADD COLUMN memory_type VARCHAR(32) DEFAULT 'project'",
            "ALTER TABLE memories ADD COLUMN scope VARCHAR(64) DEFAULT 'project'",
            "ALTER TABLE memories ADD COLUMN lineage TEXT DEFAULT '{}'",
            "ALTER TABLE memories ADD COLUMN retrieval_metadata TEXT DEFAULT '{}'",
            "ALTER TABLE memories ADD COLUMN retrieval_count INTEGER DEFAULT 0",
            "ALTER TABLE memories ADD COLUMN last_retrieved_at DATETIME",
        ):
            try:
                await conn.execute(text(statement))
            except Exception:
                pass
    # Seed default workforce if empty
    async with async_session() as db:
        seeded = await seed_agents(db)
        if seeded:
            print(f"[JARVIS] Seeded {seeded} default agents into workforce.")
    yield
    await engine.dispose()


app = FastAPI(title="JARVIS AI OS", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Router imports ---
from .api import auth, projects, chats, files, tasks, memories, settings, agents, events, jobs, agentic_core  # noqa: E402

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(projects.router, prefix="/api/projects", tags=["projects"])
app.include_router(chats.router, prefix="/api/chats", tags=["chats"])
app.include_router(files.router, prefix="/api/files", tags=["files"])
app.include_router(tasks.router, prefix="/api/tasks", tags=["tasks"])
app.include_router(memories.router, prefix="/api/memories", tags=["memories"])
app.include_router(settings.router, prefix="/api/settings", tags=["settings"])
app.include_router(agents.router, prefix="/api/agents", tags=["agents"])
app.include_router(events.router, prefix="/api/events", tags=["events"])
app.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])
app.include_router(agentic_core.router, prefix="/api/agentic-core", tags=["agentic-core"])


# Compatibility routes used by the Vite frontend during local development.
import json  # noqa: E402
from fastapi import Depends  # noqa: E402
from fastapi.responses import StreamingResponse  # noqa: E402
from pydantic import BaseModel  # noqa: E402
from .core.config import get_settings  # noqa: E402
from .dependencies import get_ai_service, get_db  # noqa: E402
from .services.ai import AIService  # noqa: E402


class FrontendChatRequest(BaseModel):
    message: str
    history: list[dict[str, str]] = []
    systemInstruction: str | None = None
    useSearch: bool = False
    model: str | None = "gemini-3.1-flash-lite"


class TranscribeRequest(BaseModel):
    audioData: str
    mimeType: str = "audio/webm"


@app.get("/api/config")
async def frontend_config():
    settings = get_settings()
    return {"hasApiKey": bool(settings.GEMINI_API_KEY), "appUrl": settings.APP_URL}


@app.post("/api/chat")
async def frontend_chat(
    data: FrontendChatRequest,
    ai_service: AIService = Depends(get_ai_service),
    db=Depends(get_db),
):
    """Streaming chat endpoint with integrated JARVIS function-calling tool loop."""
    async def event_generator():
        async for chunk in ai_service.stream_chat(
            message=data.message,
            history=data.history,
            system_instruction=data.systemInstruction
            or "You are JARVIS, an advanced AI Operating System. Answer elegantly, with a technical, refined, and helpful persona. You can create projects, agents, tasks, and save memories using your available tools.",
            model=data.model or "gemini-3.1-flash-lite",
            use_search=data.useSearch,
            db=db,
        ):
            if "error" in chunk:
                yield f"data: {json.dumps({'error': chunk['error']})}\n\n"
                return
            if chunk.get("done"):
                yield "data: [DONE]\n\n"
                return
            if "workspaceChanged" in chunk:
                yield f"data: {json.dumps({'workspaceChanged': chunk['workspaceChanged']})}\n\n"
                continue
            if "toolCall" in chunk:
                yield f"data: {json.dumps({'toolCall': chunk['toolCall']})}\n\n"
                continue

            search_chunks = [
                {"web": {"uri": c.get("uri", ""), "title": c.get("title", "")}}
                for c in chunk.get("searchChunks", [])
            ]
            yield f"data: {json.dumps({'text': chunk.get('text', ''), 'searchChunks': search_chunks})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/api/transcribe")
async def frontend_transcribe(
    data: TranscribeRequest,
    ai_service: AIService = Depends(get_ai_service),
):
    text = await ai_service.transcribe_audio(data.audioData, data.mimeType)
    return {"text": text}


@app.get("/api/health")
async def health():
    return {"status": "online", "service": "JARVIS AI OS"}
