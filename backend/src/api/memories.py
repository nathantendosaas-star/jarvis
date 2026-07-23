from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from ..dependencies import get_db
from ..schemas.memory import MemoryCreate, MemoryResponse
from ..services.memory import MemoryService
from .auth import get_current_user

router = APIRouter(dependencies=[Depends(get_current_user)])

@router.post("/", response_model=MemoryResponse, status_code=status.HTTP_201_CREATED)
async def create_memory(data: MemoryCreate, db: AsyncSession = Depends(get_db)):
    return await MemoryService.create_memory(db, data)

@router.get("/{project_id}", response_model=List[MemoryResponse])
async def get_memories(project_id: str, db: AsyncSession = Depends(get_db)):
    return await MemoryService.get_memories(db, project_id)

@router.delete("/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_memory(memory_id: str, db: AsyncSession = Depends(get_db)):
    success = await MemoryService.delete_memory(db, memory_id)
    if not success:
        raise HTTPException(status_code=404, detail="Memory not found")
    return None
