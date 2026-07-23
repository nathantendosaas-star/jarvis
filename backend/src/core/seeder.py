"""Default agent workforce seeder — runs on startup if the agents table is empty."""

import json
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from ..models.agent import Agent

DEFAULT_AGENTS = [
    {
        "name": "Developer",
        "role": "Full-stack Engineer",
        "avatar": "💻",
        "status": "idle",
        "priority": "high",
        "cpu_allocation": 60,
        "memory_allocation": 256,
        "capabilities": ["Code generation", "Debugging", "Refactoring", "Architecture design"],
        "tools": ["read_file_content", "write_file_content", "create_task"],
        "activity": ["Awaiting task assignment"],
        "performance": 97,
    },
    {
        "name": "Researcher",
        "role": "Knowledge & Search Specialist",
        "avatar": "🔍",
        "status": "idle",
        "priority": "medium",
        "cpu_allocation": 40,
        "memory_allocation": 128,
        "capabilities": ["Web research", "Summarization", "Fact extraction", "Citation tracking"],
        "tools": ["save_memory", "read_file_content"],
        "activity": ["Awaiting research directive"],
        "performance": 94,
    },
    {
        "name": "Architect",
        "role": "Systems Design Engineer",
        "avatar": "🏗️",
        "status": "idle",
        "priority": "high",
        "cpu_allocation": 50,
        "memory_allocation": 192,
        "capabilities": ["System design", "Dependency mapping", "Scalability analysis", "API design"],
        "tools": ["create_project", "create_task", "write_file_content"],
        "activity": ["On standby"],
        "performance": 99,
    },
    {
        "name": "QA Engineer",
        "role": "Verification & Testing Agent",
        "avatar": "🧪",
        "status": "idle",
        "priority": "medium",
        "cpu_allocation": 35,
        "memory_allocation": 128,
        "capabilities": ["Test generation", "Error analysis", "Regression detection", "Coverage reporting"],
        "tools": ["read_file_content", "update_task_status"],
        "activity": ["Awaiting verification task"],
        "performance": 91,
    },
    {
        "name": "Memory Manager",
        "role": "Knowledge Consolidation Agent",
        "avatar": "🧠",
        "status": "working",
        "priority": "low",
        "cpu_allocation": 20,
        "memory_allocation": 64,
        "capabilities": ["Memory indexing", "Importance ranking", "Context compression", "Knowledge linking"],
        "tools": ["save_memory"],
        "activity": ["Consolidating session context"],
        "performance": 100,
    },
]


async def seed_agents(db: AsyncSession) -> int:
    """Insert default agents only if the agents table is empty. Returns count inserted."""
    result = await db.execute(select(func.count()).select_from(Agent))
    count = result.scalar_one()
    if count > 0:
        return 0  # Already seeded — skip

    import uuid
    inserted = 0
    for data in DEFAULT_AGENTS:
        agent = Agent(
            id=str(uuid.uuid4()),
            name=data["name"],
            role=data["role"],
            avatar=data["avatar"],
            status=data["status"],
            priority=data["priority"],
            cpu_allocation=data["cpu_allocation"],
            memory_allocation=data["memory_allocation"],
            capabilities=json.dumps(data["capabilities"]),
            tools=json.dumps(data["tools"]),
            activity=json.dumps(data["activity"]),
            performance=data["performance"],
        )
        db.add(agent)
        inserted += 1

    await db.commit()
    return inserted
