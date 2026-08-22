import os
import requests
from typing import Dict, Any

OLLAMA_HEALTH_URL = os.getenv("OLLAMA_HEALTH_URL", "http://localhost:11434/api/tags")
LOCAL_BRIDGE_URL = os.getenv("LOCAL_BRIDGE_URL", "http://localhost:8005/api/local-agent/execute")

SIMPLE_TASK_KEYWORDS = [
    "read", "list", "show", "check", "find", "search", "create simple", "echo",
    "offline", "simple task", "local test", "draft", "format"
]


def check_internet() -> bool:
    """Checks if internet connectivity is available."""
    try:
        r = requests.get("https://openrouter.ai/api/v1/models", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


def check_ollama_status() -> bool:
    """Checks if local Ollama server is running."""
    try:
        r = requests.get(OLLAMA_HEALTH_URL, timeout=2)
        return r.status_code == 200
    except Exception:
        return False


def is_simple_task(prompt: str) -> bool:
    """Heuristic determination if task is simple enough for local model."""
    prompt_lower = prompt.lower().strip()
    if len(prompt_lower) < 150 and any(kw in prompt_lower for kw in SIMPLE_TASK_KEYWORDS):
        return True
    return False


def route_task(prompt: str, session_id: str = None) -> Dict[str, Any]:
    """Routes user prompt to either local model bridge or cloud model suite."""
    has_internet = check_internet()
    ollama_active = check_ollama_status()

    # Route to local model if offline or if task is simple and local model is active
    if not has_internet or (ollama_active and is_simple_task(prompt)):
        if not ollama_active:
            return {
                "engine": "offline_fallback_failed",
                "response": "Offline mode detected, but local Ollama service ('jarvis-local') is not running. Please start 'ollama serve' in terminal.",
                "routed_to": "none"
            }

        try:
            res = requests.post(
                LOCAL_BRIDGE_URL,
                json={"task": prompt, "session_id": session_id, "require_review": True},
                timeout=120
            )
            res.raise_for_status()
            data = res.json()
            return {
                "engine": "local_agent_bridge",
                "response": data.get("final_answer", ""),
                "staged_files": data.get("staged_files", []),
                "mode": "OFFLINE - Staged for Cloud Review" if not has_internet else "LOCAL EXECUTION",
                "routed_to": "jarvis-local"
            }
        except Exception as e:
            # Fallback direct execution if bridge HTTP endpoint is down
            from jarvis_agent_pro import run_agentic_workflow
            workflow_res = run_agentic_workflow(user_goal=prompt, staging=True)
            return {
                "engine": "local_direct_script",
                "response": workflow_res.get("final_answer", ""),
                "staged_files": workflow_res.get("staged_files", []),
                "mode": "OFFLINE DIRECT - Staged for Cloud Review",
                "routed_to": "jarvis_agent_pro.py"
            }

    # Cloud Execution route
    return {
        "engine": "cloud_agentic_core",
        "mode": "ONLINE CLOUD ENGINE",
        "routed_to": "gemini/openrouter",
        "requires_cloud_processing": True
    }


if __name__ == "__main__":
    import sys
    task = sys.argv[1] if len(sys.argv) > 1 else "List directory files"
    print(f"Routing task: '{task}'")
    result = route_task(task)
    print(result)
