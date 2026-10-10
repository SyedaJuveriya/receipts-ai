
from fastapi import APIRouter, HTTPException

from app.models.memory import MemoryCreate, MemoryRecord
from app.services.memory_intelligence import classify_memory
from app.services.memory_store import MemoryStore

router = APIRouter(prefix="/memories", tags=["memories"])

memory_store = MemoryStore()


@router.post("")
def create_memory(data: MemoryCreate):
    try:
        candidates = memory_store.search(data.content, limit=5)

        decision = classify_memory(data.content, candidates)

        if decision.relationship.value == "DUPLICATE":
            existing = memory_store.get_by_id(
                decision.related_memory_id
            )
            return {
                "message": "Duplicate memory detected",
                "memory": existing,
                "relationship": decision.relationship.value,
            }

        memory = MemoryRecord(
            content=data.content,
            memory_type=data.memory_type,
            due_at=data.due_at,
            relationship=decision.relationship,
            related_memory_id=decision.related_memory_id,
            status=(
                "REVIEW_REQUIRED"
                if decision.requires_review
                else "ACTIVE"
            ),
        )

        memory_store.save(memory)

        return {
            "memory": memory,
            "relationship": decision.relationship.value,
            "requires_review": decision.requires_review,
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Failed to process memory",
        ) from exc


@router.get("/search")
def search_memories(q: str, limit: int = 5):
    if not q.strip():
        raise HTTPException(
            status_code=400,
            detail="Search query cannot be empty",
        )

    if not 1 <= limit <= 20:
        raise HTTPException(
            status_code=400,
            detail="Limit must be between 1 and 20",
        )

    try:
        return {"results": memory_store.search(q, limit)}
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Failed to search memories",
        ) from exc
