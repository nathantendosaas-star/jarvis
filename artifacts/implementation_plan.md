# Implementation Plan - JARVIS Backend Architecture Transition

This implementation plan outlines the steps to build the production-grade Python FastAPI backend for the **JARVIS AI Operating System** and transition the React frontend from the Express mockup.

For full architectural details, review the [JARVIS Backend Architecture Specification](file:///C:/Users/User/.gemini/antigravity/brain/9eb6d713-9471-4e59-80d2-87338725d944/jarvis_architecture.md).

## User Review Required

> [!IMPORTANT]
> The backend shifts from the Express mockup (`server.ts`) to Python FastAPI.
> To run the entire workspace (both Vite React frontend and FastAPI backend) concurrently with a single command, we will use a custom `start-dev.js` script mapped to `npm run dev`.

## Open Questions

> [!NOTE]
> There are no remaining open blocking questions. We have aligned on the following:
> - Decoupled development setup with automatic proxying.
> - Async SQLite backend in WAL mode with indexed relationships for near-instant queries.
> - Server-Sent Events (SSE) for chat response streaming.
> - In-process asyncio event bus.
> - File storage in `.storage/uploads`.
> - Authentication via environment variable password verification.
> - Background execution using FastAPI `BackgroundTasks`.

---

## Proposed Changes

### 1. Project Startup and Configuration

#### [NEW] [start-dev.js](file:///e:/nate/GEMINI%20AGENT/JARVIS/start-dev.js)
A Node.js script using child processes to concurrently boot both the Python FastAPI backend and the Vite dev server.

#### [MODIFY] [package.json](file:///e:/nate/GEMINI%20AGENT/JARVIS/package.json)
Change the `"dev"` script from `"tsx server.ts"` to `"node start-dev.js"`.

#### [MODIFY] [vite.config.ts](file:///e:/nate/GEMINI%20AGENT/JARVIS/vite.config.ts)
Add reverse proxy middleware definitions forwarding `/api` to `http://127.0.0.1:8000`.

#### [NEW] [requirements.txt](file:///e:/nate/GEMINI%20AGENT/JARVIS/requirements.txt)
Define backend packages: `fastapi`, `uvicorn`, `sqlalchemy[asyncio]`, `aiosqlite`, `alembic`, `pydantic`, `google-genai`, `python-dotenv`, `python-multipart`.

#### [NEW] [.env](file:///e:/nate/GEMINI%20AGENT/JARVIS/.env)
Define configurations: `GEMINI_API_KEY`, `JARVIS_PASSWORD`, `DATABASE_URL=sqlite+aiosqlite:///./.storage/jarvis.db`, `STORAGE_DIR=./.storage/uploads`.

---

### 2. Backend Modules & DB Setup

#### [NEW] [database.py](file:///e:/nate/GEMINI%20AGENT/JARVIS/backend/src/core/database.py)
SQLAlchemy async engine setup with SQLite WAL pragma configurations.

#### [NEW] [models](file:///e:/nate/GEMINI%20AGENT/JARVIS/backend/src/models/)
Create DB model classes: `project.py`, `chat.py`, `file.py`, `memory.py`, `task.py` with foreign key indexes for optimized search performance.

#### [NEW] [schemas](file:///e:/nate/GEMINI%20AGENT/JARVIS/backend/src/schemas/)
Pydantic schemas for request validation and serialization.

---

### 3. Service Layer

#### [NEW] [ai.py](file:///e:/nate/GEMINI%20AGENT/JARVIS/backend/src/services/ai.py)
Implement the `google-genai` integration with streaming yield loops.

#### [NEW] [services](file:///e:/nate/GEMINI%20AGENT/JARVIS/backend/src/services/)
Implement core business logic files: `chat.py`, `project.py`, `file.py`, `task.py`, `memory.py`.

---

### 4. API Endpoints

#### [NEW] [routers](file:///e:/nate/GEMINI%20AGENT/JARVIS/backend/src/api/)
FastAPI routers for REST endpoints: `auth.py`, `projects.py`, `chats.py`, `files.py`, `tasks.py`, `memories.py`.

#### [NEW] [main.py](file:///e:/nate/GEMINI%20AGENT/JARVIS/backend/src/main.py)
Standard FastAPI application setup, middleware parameters, database initialization hook, and routing inclusions.

---

## Verification Plan

### Automated Tests
We will run automated python tests using `pytest` inside the backend directory:
- Run service tests: `pytest backend/tests/test_services.py`
- Run API routing tests: `pytest backend/tests/test_api.py`

### Manual Verification
1. Run everything using a single command: `npm run dev`.
2. Open browser to verify:
   - Dashboard statistics load successfully.
   - Creating projects saves data to SQLite database.
   - File upload stores binary files in `.storage/uploads` and updates File list.
   - Chat streaming with Gemini executes cleanly via Server-Sent Events.
   - Tasks execute and update state in real-time.
