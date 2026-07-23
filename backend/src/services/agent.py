"""AgentService — CRUD operations for the Agent workforce database table."""

import uuid
import json
from typing import List, Optional
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from ..models.agent import Agent
from ..schemas.agent import AgentCreate, AgentUpdate
from ..core.events import event_broker


def _encode(value: list | None) -> str:
    """Serialize a Python list to a JSON string for SQLite storage."""
    return json.dumps(value or [])


class AgentService:

    @staticmethod
    async def create_agent(db: AsyncSession, data: AgentCreate) -> Agent:
        agent = Agent(
            id=str(uuid.uuid4()),
            name=data.name,
            role=data.role,
            avatar=data.avatar,
            status=data.status,
            current_task=data.current_task,
            priority=data.priority,
            cpu_allocation=data.cpu_allocation,
            memory_allocation=data.memory_allocation,
            capabilities=_encode(data.capabilities),
            tools=_encode(data.tools),
            activity=_encode(data.activity),
            performance=data.performance,
        )
        db.add(agent)
        await db.flush()
        await event_broker.publish("AgentCreated", {"agent_id": agent.id, "name": agent.name})
        return agent

    @staticmethod
    async def get_agents(db: AsyncSession) -> List[Agent]:
        result = await db.execute(select(Agent).order_by(desc(Agent.created_at)))
        return list(result.scalars().all())

    @staticmethod
    async def get_agent(db: AsyncSession, agent_id: str) -> Optional[Agent]:
        return await db.get(Agent, agent_id)

    @staticmethod
    async def update_agent(db: AsyncSession, agent_id: str, data: AgentUpdate) -> Optional[Agent]:
        agent = await db.get(Agent, agent_id)
        if not agent:
            return None

        update_data = data.model_dump(exclude_unset=True)

        # Lists must be re-serialized to JSON before writing
        for list_field in ("capabilities", "tools", "activity"):
            if list_field in update_data:
                update_data[list_field] = _encode(update_data[list_field])

        for key, value in update_data.items():
            setattr(agent, key, value)

        await db.flush()
        await event_broker.publish("AgentUpdated", {
            "agent_id": agent.id,
            "status": agent.status,
            "priority": agent.priority,
        })
        return agent

    @staticmethod
    async def delete_agent(db: AsyncSession, agent_id: str) -> bool:
        agent = await db.get(Agent, agent_id)
        if not agent:
            return False
        await db.delete(agent)
        await db.flush()
        await event_broker.publish("AgentDecommissioned", {"agent_id": agent_id})
        return True
