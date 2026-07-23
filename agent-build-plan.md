# JARVIS AI OS — Agent Workforce & Tool Integration Plan

This plan details the steps required to give the central chat model the ability to manage specialized AI agents, create projects, assign tasks, write files, and interact with the entire workspace database.

---

## 1. Database Layer: Agent Storage

Currently, the database only stores `Project`, `Chat`, `Message`, `File`, `Task`, and `Memory` models. We need to create an `Agent` model for persistent tracking of the specialized workforce.

### `backend/src/models/agent.py`
Create a database table definition representing the AI agent state:
* `id` (UUID string, Primary Key)
* `name` (String, e.g., "Developer", "Researcher")
* `role` (String, e.g., "Full-stack Engineer")
* `avatar` (String, e.g., "🤖", "📈")
* `status` (String, default `"idle"`; can be `"working"`, `"paused"`, or `"idle"`)
* `current_task` (String, Nullable, description of current work)
* `priority` (String, default `"medium"`; can be `"high"`, `"medium"`, `"low"`)
* `cpu_allocation` (Integer, default `50` percent)
* `memory_allocation` (Integer, default `128` MB)
* `capabilities` (JSON / Text, array of capability strings)
* `tools` (JSON / Text, array of tool access strings)

### Register Model in Metadata
Import the `Agent` model in [backend/src/models/\_\_init\_\_.py](file:///E:/nate/GEMINI%20AGENT/JARVIS/backend/src/models/__init__.py) so that SQLite auto-generates the table on application startup.

---

## 2. Backend API: Agent CRUD

Define Pydantic schemas and add REST endpoints to retrieve and modify the agent list from the frontend.

### `backend/src/schemas/agent.py`
* Create `AgentBase`, `AgentCreate`, `AgentUpdate`, and `AgentResponse` schemas.

### `backend/src/api/agents.py`
Expose endpoints for the frontend to interact with:
* `GET /api/agents/`: Retrieve all registered agents.
* `POST /api/agents/`: Register a new agent.
* `PATCH /api/agents/{agent_id}`: Update an agent's status, priority, or allocations.
* `DELETE /api/agents/{agent_id}`: Decommission/remove an agent.

Include this router in `backend/src/main.py` under the `/api/agents` prefix.

---

## 3. Frontend Integration: Sync UI state

Currently, `src/App.tsx` initializes agents to an empty array:
```typescript
const [agents, setAgents] = useState<Agent[]>([]);
```

### Steps:
1. Update [src/api.ts](file:///E:/nate/GEMINI%20AGENT/JARVIS/src/api.ts) to define api callers:
   * `fetchAgents()`, `createAgent()`, `updateAgent()`, and `deleteAgent()`.
2. Connect `App.tsx` [reloadWorkspaceData](file:///E:/nate/GEMINI%20AGENT/JARVIS/src/App.tsx#L70) to fetch real agent data from the backend.
3. Update [AgentsView.tsx](file:///E:/nate/GEMINI%20AGENT/JARVIS/src/components/AgentsView.tsx) to perform backend mutations (updating CPU/memory sliders, pausing/restarting nodes, and updating priorities) using backend API requests instead of pure client-side state changes.

---

## 4. Chat Model: Function Calling (Tools)

To give the chat model control over the application state, we will introduce **Function Calling (Tools)** in the `google-genai` Python SDK.

### Define Tools in `backend/src/services/ai.py`
Register the following python helper functions as Gemini tools:

```python
# Agent Management
def create_agent(name: str, role: str, avatar: str, capabilities: list[str], tools: list[str]) -> str:
    """Create a new specialized agent in the workforce database."""

def update_agent_allocation(agent_id: str, status: str = None, priority: str = None, cpu_percent: int = None, memory_mb: int = None) -> str:
    """Modify an agent's running status, priority tier, or system resource limits."""

# Workspace & Automation
def create_project(name: str, description: str = None, color: str = None) -> str:
    """Start a new workspace project/repository."""

def create_task(project_id: str, title: str, description: str = None) -> str:
    """Create a new automation task under a specific project."""

def update_task_status(task_id: str, status: str) -> str:
    """Update task execution status (e.g. 'completed', 'failed', 'running')."""

def save_memory(text: str, type: str, importance: int) -> str:
    """Persist facts, preferences, or rules into JARVIS memory bank."""

# File Orchestration
def read_file_content(path: str) -> str:
    """Retrieve full file contents from the workspace repository."""

def write_file_content(path: str, content: str) -> str:
    """Create or overwrite files in the workspace repository."""
```

---

## 5. Execution Loop (Tool Routing)

Update [stream_chat](file:///E:/nate/GEMINI%20AGENT/JARVIS/backend/src/services/ai.py#L33) to implement the tool execution loop:

```python
# Pseudocode loop for tool orchestration
config = types.GenerateContentConfig(
    system_instruction=system_instruction,
    temperature=temperature,
    tools=[
        create_agent, update_agent_allocation,
        create_project, create_task, update_task_status,
        save_memory, read_file_content, write_file_content
    ]
)

response = await self.client.aio.models.generate_content_stream(...)

# In the generator:
async for chunk in response:
    if chunk.function_calls:
        for call in chunk.function_calls:
            # 1. Resolve function arguments and execute the local Python code
            result = await execute_tool(call.name, call.args)
            
            # 2. Yield tool execution status to frontend (so the UI shows a "Tool Executing" HUD indicator)
            yield {"toolCall": {"name": call.name, "args": call.args, "status": "completed"}}
            
            # 3. Feed the execution result back to Gemini in the conversation history
            # 4. Generate next response chunk using the tool output
```

This completes the loop, allowing the model to execute any number of tasks dynamically based on user chat commands.
