import os
import json
import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from jarvis_agent_pro import run_agentic_workflow, OLLAMA_URL, MODEL_NAME, STAGED_DIR, WORKSPACE_DIR

app = FastAPI(
    title="JARVIS Local Agent Bridge Server",
    description="Bridge HTTP server exposing jarvis-local Ollama workflow to JARVIS UI and backend",
    version="1.0.0"
)


class TaskRequest(BaseModel):
    task: str
    session_id: Optional[str] = None
    require_review: Optional[bool] = True
    context: Optional[str] = ""


class TaskResponse(BaseModel):
    status: str
    final_answer: str
    staged_files: List[str]
    session_id: Optional[str] = None


@app.get("/api/local-agent/health")
def health_check():
    """Checks local model agent health and Ollama connection status."""
    import requests
    ollama_online = False
    try:
        r = requests.get("http://localhost:11434/api/tags", timeout=3)
        ollama_online = (r.status_code == 200)
    except Exception:
        ollama_online = False

    return {
        "status": "online" if ollama_online else "degraded",
        "ollama_url": OLLAMA_URL,
        "model": MODEL_NAME,
        "ollama_connected": ollama_online,
        "workspace": WORKSPACE_DIR
    }


@app.post("/api/local-agent/execute", response_model=TaskResponse)
def execute_task(req: TaskRequest):
    """Executes a simple task using the local agent framework (jarvis_agent_pro)."""
    if not req.task.strip():
        raise HTTPException(status_code=400, detail="Task cannot be empty.")

    try:
        result = run_agentic_workflow(
            user_goal=req.task,
            conversation_history=req.context or "",
            staging=req.require_review if req.require_review is not None else True
        )
        return TaskResponse(
            status=result["status"],
            final_answer=result["final_answer"],
            staged_files=result["staged_files"],
            session_id=req.session_id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error executing local agent workflow: {str(e)}")


@app.get("/api/local-agent/staged-files")
def get_staged_files():
    """Returns manifest of files currently staged for cloud review."""
    manifest_path = os.path.join(STAGED_DIR, "manifest.json")
    if not os.path.exists(manifest_path):
        return {"staged_files": [], "manifest": None}

    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
        return {
            "staged_files": [item.get("filename") for item in manifest.get("files", [])],
            "manifest": manifest
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading staged manifest: {str(e)}")


if __name__ == "__main__":
    port = int(os.getenv("BRIDGE_PORT", 8005))
    print(f"Starting JARVIS Local Agent Bridge Server on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)
