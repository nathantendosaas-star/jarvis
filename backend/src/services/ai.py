"""AI Service — Gemini integration with streaming, tool-calling execution loop, retry, and model fallback."""

import time
import asyncio
import base64
import uuid
import json
from typing import AsyncGenerator, Dict, List, Any, Optional
from google import genai
from google.genai import types
from sqlalchemy.ext.asyncio import AsyncSession
from ..core.config import get_settings
from .events import EventService
from .context import ContextService

# Ordered fallback chain if primary model errors
FALLBACK_CHAIN = ["gemini-3.1-flash-lite", "gemini-3.5-flash"]


# ---------------------------------------------------------------------------
# JARVIS Tool Definitions
# ---------------------------------------------------------------------------
# Each function is registered with Gemini as a callable tool. The model can
# invoke them mid-stream. Results are fed back as FunctionResponse content so
# the model can reason over the tool output and continue generating.
# ---------------------------------------------------------------------------

async def _tool_create_agent(db: AsyncSession, args: Dict[str, Any]) -> str:
    """Create a new specialized agent in the workforce database."""
    from ..schemas.agent import AgentCreate
    from ..services.agent import AgentService

    data = AgentCreate(
        name=args.get("name", "New Agent"),
        role=args.get("role", "General Agent"),
        avatar=args.get("avatar", "🤖"),
        capabilities=args.get("capabilities", []),
        tools=args.get("tools", []),
    )
    agent = await AgentService.create_agent(db, data)
    return json.dumps({"success": True, "agent_id": agent.id, "name": agent.name})


async def _tool_update_agent(db: AsyncSession, args: Dict[str, Any]) -> str:
    """Modify an agent's running status, priority tier, or system resource limits."""
    from ..schemas.agent import AgentUpdate
    from ..services.agent import AgentService

    agent_id = args.get("agent_id", "")
    data = AgentUpdate(
        status=args.get("status"),
        priority=args.get("priority"),
        cpu_allocation=args.get("cpu_percent"),
        memory_allocation=args.get("memory_mb"),
        current_task=args.get("current_task"),
    )
    agent = await AgentService.update_agent(db, agent_id, data)
    if not agent:
        return json.dumps({"success": False, "error": f"Agent {agent_id} not found."})
    return json.dumps({"success": True, "agent_id": agent.id, "status": agent.status})


async def _tool_create_project(db: AsyncSession, args: Dict[str, Any]) -> str:
    """Start a new workspace project/repository."""
    from ..schemas.project import ProjectCreate
    from ..services.project import ProjectService

    data = ProjectCreate(
        name=args.get("name", "New Project"),
        description=args.get("description", ""),
        color=args.get("color", "#3b82f6"),
    )
    project = await ProjectService.create_project(db, data)
    return json.dumps({"success": True, "project_id": project.id, "name": project.name})


async def _tool_create_task(db: AsyncSession, args: Dict[str, Any]) -> str:
    """Create a new automation task under a specific project."""
    from ..schemas.task import TaskCreate
    from ..services.task import TaskService

    project_id = args.get("project_id", "")
    if not project_id:
        return json.dumps({"success": False, "error": "project_id is required."})

    data = TaskCreate(
        project_id=project_id,
        title=args.get("title", "Untitled Task"),
        description=args.get("description", ""),
    )
    task = await TaskService.create_task(db, data)
    return json.dumps({"success": True, "task_id": task.id, "title": task.title})


async def _tool_update_task_status(db: AsyncSession, args: Dict[str, Any]) -> str:
    """Update task execution status (e.g. 'completed', 'failed', 'running')."""
    from ..schemas.task import TaskUpdate
    from ..services.task import TaskService

    task_id = args.get("task_id", "")
    status = args.get("status", "running")
    data = TaskUpdate(status=status)
    task = await TaskService.update_task(db, task_id, data)
    if not task:
        return json.dumps({"success": False, "error": f"Task {task_id} not found."})
    return json.dumps({"success": True, "task_id": task.id, "status": task.status})


async def _tool_save_memory(db: AsyncSession, args: Dict[str, Any]) -> str:
    """Persist facts, preferences, or rules into JARVIS memory bank."""
    from ..schemas.memory import MemoryCreate
    from ..services.memory import MemoryService
    from ..services.project import ProjectService

    project_id = args.get("project_id")
    # Fall back to the first available project if none given
    if not project_id:
        projects = await ProjectService.get_projects(db)
        if not projects:
            return json.dumps({"success": False, "error": "No projects available. Create a project first."})
        project_id = projects[0].id

    data = MemoryCreate(
        project_id=project_id,
        title=args.get("title", "Memory"),
        content=args.get("text", ""),
        importance=min(10, max(1, int(args.get("importance", 5)))),
    )
    memory = await MemoryService.create_memory(db, data)
    return json.dumps({"success": True, "memory_id": memory.id})


async def _tool_read_file(args: Dict[str, Any]) -> str:
    """Retrieve file contents from the workspace repository."""
    from pathlib import Path
    from ..services.file import WORKSPACE_ROOT, _should_ignore

    rel_path = args.get("path", "").lstrip("/")
    target = (WORKSPACE_ROOT / rel_path).resolve()

    # Security: prevent path traversal
    try:
        target.relative_to(WORKSPACE_ROOT)
    except ValueError:
        return json.dumps({"success": False, "error": "Access denied — path escapes workspace root."})

    if _should_ignore(target):
        return json.dumps({"success": False, "error": f"File '{rel_path}' is restricted."})

    if not target.exists():
        return json.dumps({"success": False, "error": f"File '{rel_path}' not found."})

    if not target.is_file():
        return json.dumps({"success": False, "error": f"'{rel_path}' is a directory."})

    try:
        content = target.read_text(encoding="utf-8")
        return json.dumps({"success": True, "path": rel_path, "content": content[:8000]})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


async def _tool_write_file(args: Dict[str, Any]) -> str:
    """Create or overwrite files in the workspace repository."""
    from pathlib import Path
    from ..services.file import WORKSPACE_ROOT, _should_ignore, SECRET_NAMES

    rel_path = args.get("path", "").lstrip("/")
    content = args.get("content", "")
    target = (WORKSPACE_ROOT / rel_path).resolve()

    # Security checks
    try:
        target.relative_to(WORKSPACE_ROOT)
    except ValueError:
        return json.dumps({"success": False, "error": "Access denied — path escapes workspace root."})

    if target.name in SECRET_NAMES or target.name.startswith(".env"):
        return json.dumps({"success": False, "error": "Writing to secret files is not allowed."})

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return json.dumps({"success": True, "path": rel_path, "bytes_written": len(content.encode())})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


async def _tool_run_script(db: AsyncSession, args: Dict[str, Any]) -> str:
    """Launch a workspace Python script as an autonomous subprocess agent."""
    from ..services.executor import launch_script

    script_path = args.get("script_path", "")
    timeout = int(args.get("timeout", 300))

    if not script_path:
        return json.dumps({"success": False, "error": "script_path is required."})

    try:
        job_id = await launch_script(db, script_path, timeout=timeout)
        return json.dumps({
            "success": True,
            "job_id": job_id,
            "message": (
                f"Script '{script_path}' launched as job {job_id}. "
                "Call await_job with this job_id to wait for completion, "
                "then read the output_path it returns."
            ),
        })
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


async def _tool_await_job(db: AsyncSession, args: Dict[str, Any]) -> str:
    """Block until a launched subprocess job finishes. Returns the output file path."""
    from ..services.executor import wait_for_job

    job_id = args.get("job_id", "")
    if not job_id:
        return json.dumps({"success": False, "error": "job_id is required."})

    result = await wait_for_job(db, job_id)
    return json.dumps(result)


# ---------------------------------------------------------------------------
# Tool dispatch table
# ---------------------------------------------------------------------------
TOOL_DISPATCH = {
    "create_agent": _tool_create_agent,
    "update_agent_allocation": _tool_update_agent,
    "create_project": _tool_create_project,
    "create_task": _tool_create_task,
    "update_task_status": _tool_update_task_status,
    "save_memory": _tool_save_memory,
    "read_file_content": _tool_read_file,
    "write_file_content": _tool_write_file,
    "run_script": _tool_run_script,
    "await_job": _tool_await_job,
}

# Gemini function declarations (schema for the model)
JARVIS_TOOLS = [
    types.Tool(function_declarations=[
        types.FunctionDeclaration(
            name="create_agent",
            description="Create a new specialized AI agent in the JARVIS workforce database.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "name": types.Schema(type=types.Type.STRING, description="Human-readable agent name, e.g. 'Developer'"),
                    "role": types.Schema(type=types.Type.STRING, description="Agent's functional role, e.g. 'Full-stack Engineer'"),
                    "avatar": types.Schema(type=types.Type.STRING, description="Single emoji avatar, e.g. '🤖'"),
                    "capabilities": types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING)),
                    "tools": types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING)),
                },
                required=["name", "role"],
            ),
        ),
        types.FunctionDeclaration(
            name="update_agent_allocation",
            description="Modify an agent's running status, priority tier, current task, or resource limits.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "agent_id": types.Schema(type=types.Type.STRING, description="UUID of the agent to update"),
                    "status": types.Schema(type=types.Type.STRING, description="idle | working | paused | offline"),
                    "priority": types.Schema(type=types.Type.STRING, description="high | medium | low"),
                    "current_task": types.Schema(type=types.Type.STRING),
                    "cpu_percent": types.Schema(type=types.Type.INTEGER, description="0-100"),
                    "memory_mb": types.Schema(type=types.Type.INTEGER, description="0-512"),
                },
                required=["agent_id"],
            ),
        ),
        types.FunctionDeclaration(
            name="create_project",
            description="Start a new workspace project/repository.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "name": types.Schema(type=types.Type.STRING),
                    "description": types.Schema(type=types.Type.STRING),
                    "color": types.Schema(type=types.Type.STRING, description="Hex color e.g. #3b82f6"),
                },
                required=["name"],
            ),
        ),
        types.FunctionDeclaration(
            name="create_task",
            description="Create a new automation task under a specific project.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "project_id": types.Schema(type=types.Type.STRING),
                    "title": types.Schema(type=types.Type.STRING),
                    "description": types.Schema(type=types.Type.STRING),
                },
                required=["project_id", "title"],
            ),
        ),
        types.FunctionDeclaration(
            name="update_task_status",
            description="Update a task's execution status.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "task_id": types.Schema(type=types.Type.STRING),
                    "status": types.Schema(type=types.Type.STRING, description="queued | running | completed | failed | cancelled"),
                },
                required=["task_id", "status"],
            ),
        ),
        types.FunctionDeclaration(
            name="save_memory",
            description="Persist a fact, preference, or rule into the JARVIS memory bank.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "text": types.Schema(type=types.Type.STRING, description="The memory content to store"),
                    "title": types.Schema(type=types.Type.STRING),
                    "importance": types.Schema(type=types.Type.INTEGER, description="1 (low) to 10 (critical)"),
                    "project_id": types.Schema(type=types.Type.STRING, description="Optional: project to scope memory under"),
                },
                required=["text"],
            ),
        ),
        types.FunctionDeclaration(
            name="read_file_content",
            description="Read full file contents from the workspace.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "path": types.Schema(type=types.Type.STRING, description="Workspace-relative path, e.g. 'src/App.tsx'"),
                },
                required=["path"],
            ),
        ),
        types.FunctionDeclaration(
            name="write_file_content",
            description="Create or overwrite a file in the workspace.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "path": types.Schema(type=types.Type.STRING),
                    "content": types.Schema(type=types.Type.STRING),
                },
                required=["path", "content"],
            ),
        ),
        types.FunctionDeclaration(
            name="run_script",
            description=(
                "Launch a Python script from the workspace as an autonomous subprocess agent. "
                "The script runs in the background. Returns a job_id to track execution. "
                "Use this to run lead scrapers, data processors, or any automation script."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "script_path": types.Schema(
                        type=types.Type.STRING,
                        description="Workspace-relative path to the .py script, e.g. 'backend/scripts/lead_scraper.py'",
                    ),
                    "timeout": types.Schema(
                        type=types.Type.INTEGER,
                        description="Max seconds to allow the script to run before killing it. Default 300.",
                    ),
                },
                required=["script_path"],
            ),
        ),
        types.FunctionDeclaration(
            name="await_job",
            description=(
                "Wait for a previously launched subprocess job to finish. "
                "Blocks until the script signals completion or fails. "
                "Returns the output file path on success — then call read_file_content on that path."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "job_id": types.Schema(
                        type=types.Type.STRING,
                        description="The job_id returned by run_script",
                    ),
                },
                required=["job_id"],
            ),
        ),
    ])
]


async def _execute_tool(name: str, args: Dict[str, Any], db: Optional[AsyncSession]) -> str:
    """Dispatch a tool call to its Python implementation and return the result string."""
    handler = TOOL_DISPATCH.get(name)
    if not handler:
        return json.dumps({"success": False, "error": f"Unknown tool: {name}"})

    try:
        # File-only tools don't need the DB session
        if name in ("read_file_content", "write_file_content"):
            return await handler(args)
        else:
            if db is None:
                return json.dumps({"success": False, "error": "No database session available for this tool."})
            return await handler(db, args)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


class AIService:
    """Wraps the google-genai SDK with streaming, retry, fallback, and JARVIS function-calling."""

    def __init__(self):
        settings = get_settings()
        self.client = (
            genai.Client(api_key=settings.GEMINI_API_KEY)
            if settings.GEMINI_API_KEY
            else None
        )

    def _ensure_client(self):
        if self.client is None:
            settings = get_settings()
            if not settings.GEMINI_API_KEY:
                raise RuntimeError("GEMINI_API_KEY not configured. Set it in your .env file.")
            self.client = genai.Client(api_key=settings.GEMINI_API_KEY)

    async def stream_chat(
        self,
        message: str,
        history: List[Dict[str, str]],
        system_instruction: str = "You are JARVIS, an advanced AI Operating System. Answer elegantly, with a technical, refined, and helpful persona.",
        model: str = "gemini-3.1-flash-lite",
        use_search: bool = False,
        temperature: float = 0.7,
        db: Optional[AsyncSession] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream a chat completion from Gemini with full JARVIS tool-call execution loop.

        Yields dicts with keys:
        - 'text' + 'searchChunks': streaming response text
        - 'toolCall': tool execution event (name, args, result, status)
        - 'done': final done marker with latency/token metadata
        - 'error': unrecoverable error
        """
        self._ensure_client()

        correlation_id = str(uuid.uuid4())
        enriched_message, context_trace = await ContextService.assemble(message, db)
        await EventService.record(db, "objective.started", status="running", correlation_id=correlation_id, metadata={"context": context_trace})

        # Build content sequence from history + current message
        contents: List[types.Content] = []
        for msg in history:
            role = "user" if msg.get("role") == "user" else "model"
            contents.append(
                types.Content(role=role, parts=[types.Part.from_text(text=msg.get("content", ""))])
            )
        contents.append(
            types.Content(role="user", parts=[types.Part.from_text(text=enriched_message)])
        )

        # Build generation config — tools mutually exclusive with Google Search
        tools_to_use = JARVIS_TOOLS if not use_search else [types.Tool(google_search=types.GoogleSearch())]

        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=temperature,
            tools=tools_to_use,
        )

        # Approve only known models; clamp unknown IDs to Flash Lite
        primary_model = model if model in FALLBACK_CHAIN else "gemini-3.1-flash-lite"
        models_to_try = [primary_model] + [m for m in FALLBACK_CHAIN if m != primary_model]
        last_error = None

        for attempt_model in models_to_try:
            retries = 0
            while retries < 2:
                try:
                    start = time.monotonic()
                    token_count = 0
                    grounding_chunks: list = []

                    # -------------------------------------------------------
                    # Agentic loop: keep calling the model until no more tool
                    # calls are returned (function call → execute → respond).
                    # -------------------------------------------------------
                    current_contents = list(contents)

                    while True:
                        response = await self.client.aio.models.generate_content_stream(
                            model=attempt_model,
                            contents=current_contents,
                            config=config,
                        )

                        # Collect all chunks, streaming text as we go
                        collected_parts: List[types.Part] = []
                        function_calls_found: List[types.FunctionCall] = []
                        text_buffer = ""

                        async for chunk in response:
                            # --- Text streaming ---
                            text = chunk.text or ""
                            if text:
                                token_count += len(text.split())
                                text_buffer += text

                                # Extract grounding metadata if search was used
                                search_chunks: list = []
                                if hasattr(chunk, "candidates") and chunk.candidates:
                                    meta = getattr(chunk.candidates[0], "grounding_metadata", None)
                                    if meta and hasattr(meta, "grounding_chunks") and meta.grounding_chunks:
                                        grounding_chunks = meta.grounding_chunks
                                        search_chunks = [
                                            {
                                                "uri": getattr(getattr(c, "web", None), "uri", ""),
                                                "title": getattr(getattr(c, "web", None), "title", ""),
                                            }
                                            for c in grounding_chunks
                                            if hasattr(c, "web")
                                        ]
                                yield {"text": text, "searchChunks": search_chunks}

                            # --- Function call detection ---
                            if hasattr(chunk, "candidates") and chunk.candidates:
                                candidate = chunk.candidates[0]
                                if hasattr(candidate, "content") and candidate.content:
                                    for part in candidate.content.parts or []:
                                        if hasattr(part, "function_call") and part.function_call:
                                            function_calls_found.append(part.function_call)
                                        collected_parts.append(part)

                        # If no function calls, the model is done
                        if not function_calls_found:
                            break

                        # -------------------------------------------------------
                        # Execute each function call and feed results back
                        # -------------------------------------------------------
                        model_content = types.Content(role="model", parts=collected_parts)
                        current_contents.append(model_content)

                        function_response_parts: List[types.Part] = []
                        for fc in function_calls_found:
                            call_args = dict(fc.args) if fc.args else {}

                            # Notify the frontend a tool is executing
                            yield {
                                "toolCall": {
                                    "name": fc.name,
                                    "args": call_args,
                                    "status": "running",
                                }
                            }

                            result_str = await _execute_tool(fc.name, call_args, db)

                            # Notify the frontend the tool completed
                            yield {
                                "toolCall": {
                                    "name": fc.name,
                                    "args": call_args,
                                    "result": result_str,
                                    "status": "completed",
                                }
                            }

                            # Broadcast workspace changed event for all mutations
                            if fc.name in (
                                "create_agent",
                                "update_agent_allocation",
                                "create_project",
                                "create_task",
                                "update_task_status",
                                "save_memory",
                                "run_script",
                                "write_file_content",
                            ):
                                yield {"workspaceChanged": correlation_id}

                            function_response_parts.append(
                                types.Part.from_function_response(
                                    name=fc.name,
                                    response={"result": result_str},
                                )
                            )

                        # Append tool results as user content and loop back
                        current_contents.append(
                            types.Content(role="user", parts=function_response_parts)
                        )

                    # End of agentic loop — success
                    latency = time.monotonic() - start
                    yield {
                        "done": True,
                        "latency": round(latency, 3),
                        "token_count": token_count,
                        "model_used": attempt_model,
                    }
                    return

                except Exception as e:
                    last_error = e
                    err_str = str(e)
                    is_transient = any(
                        s in err_str
                        for s in ["503", "429", "UNAVAILABLE", "overloaded", "ResourceExhausted"]
                    )
                    if is_transient and retries < 1:
                        retries += 1
                        await asyncio.sleep(retries)
                        continue
                    break  # Move to next model in fallback chain

        # All models exhausted
        yield {"error": str(last_error) if last_error else "All models failed"}

    async def transcribe_audio(self, audio_b64: str, mime_type: str = "audio/webm") -> str:
        """Transcribe base64-encoded audio using a fast Gemini model."""
        self._ensure_client()
        audio_bytes = base64.b64decode(audio_b64)
        response = await self.client.aio.models.generate_content(
            model="gemini-3.1-flash-lite",
            contents=[
                types.Part.from_bytes(data=audio_bytes, mime_type=mime_type),
                types.Part.from_text(
                    text="Accurately transcribe this audio. Output ONLY the transcribed words."
                ),
            ],
        )
        return response.text or ""
