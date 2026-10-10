from fastapi import APIRouter, HTTPException

from app.models.memory import MemoryCreate, MemoryRecord
from app.services.memory_store import MemoryStore

router = APIRouter(prefix="/memories", tags=["memories"])

memory_store = MemoryStore()


@router.post("")
def create_memory(data: MemoryCreate):
    memory = MemoryRecord(
        content=data.content,
        memory_type=data.memory_type,
        due_at=data.due_at,
    )

    try:
        memory_store.save(memory)
        return memory
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Failed to save memory",
        ) from exc


@router.get("/search")
def search_memories(q: str, limit: int = 5):
    if not q.strip():
        raise HTTPException(status_code=400, detail="Search query cannot be empty")

    if not 1 <= limit <= 20:
        raise HTTPException(status_code=400, detail="Limit must be between 1 and 20")

    try:
        return {"results": memory_store.search(q, limit)}
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Failed to search memories",
        ) from exc