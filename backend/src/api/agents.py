"""REST API router for the Agent workforce — CRUD endpoints for the frontend and AI tool-calls."""

import asyncio
import os
import sys
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from ..dependencies import get_db
from ..schemas.agent import AgentCreate, AgentUpdate, AgentResponse
from ..services.agent import AgentService
from .auth import get_current_user

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/", response_model=List[AgentResponse])
async def list_agents(db: AsyncSession = Depends(get_db)):
    """Return all registered agents ordered by creation date (newest first)."""
    return await AgentService.get_agents(db)


@router.post("/", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(data: AgentCreate, db: AsyncSession = Depends(get_db)):
    """Register a new agent in the workforce database."""
    return await AgentService.create_agent(db, data)


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: str, db: AsyncSession = Depends(get_db)):
    """Retrieve a single agent by ID."""
    agent = await AgentService.get_agent(db, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.patch("/{agent_id}", response_model=AgentResponse)
async def update_agent(agent_id: str, data: AgentUpdate, db: AsyncSession = Depends(get_db)):
    """Update an agent's status, priority, resource allocations, or task description."""
    agent = await AgentService.update_agent(db, agent_id, data)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(agent_id: str, delete_cache: bool = False, db: AsyncSession = Depends(get_db)):
    """Decommission and remove an agent from the workforce, optionally deleting their cache files."""
    success = await AgentService.delete_agent(db, agent_id, delete_cache=delete_cache)
    if not success:
        raise HTTPException(status_code=404, detail="Agent not found")
    return None


@router.post("/review-staged", response_model=Dict[str, Any])
async def review_staged_offline_changes():
    """Trigger cloud model static review and merge of offline staged files asynchronously."""
    try:
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
        if root_dir not in sys.path:
            sys.path.insert(0, root_dir)

        import cloud_review
        # Run synchronous cloud review network call in a thread pool to avoid blocking event loop
        return await asyncio.to_thread(cloud_review.approve_and_merge_staged_changes)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to review staged changes: {str(e)}")
