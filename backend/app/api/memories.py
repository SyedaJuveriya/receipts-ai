
import json
import httpx

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.models.memory import MemoryCreate, MemoryRecord
from app.services.lyzr_service import lyzr_service
from app.services.memory_intelligence import classify_memory
from app.services.memory_store import MemoryStore

router = APIRouter(prefix="/memories", tags=["memories"])

memory_store = MemoryStore()


class LyzrExtractRequest(BaseModel):
    message: str = Field(min_length=1, max_length=5000)


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


@router.post("/extract")
async def extract_memories_with_lyzr(data: LyzrExtractRequest):
    try:
        result = await lyzr_service.extract_memories(data.message)

        raw_response = result.get("response", result)

        if isinstance(raw_response, str):
            extracted = json.loads(raw_response)
        elif isinstance(raw_response, dict):
            extracted = raw_response
        else:
            raise ValueError("Unexpected Lyzr response format")

        memories = extracted.get("memories", [])

        if not isinstance(memories, list):
            raise ValueError("Expected a memories list")

        saved = []
        duplicates = []

        for item in memories:
            if not isinstance(item, dict):
                continue

            content = str(item.get("content", "")).strip()
            if not content:
                continue

            try:
                memory_type = MemoryCreate(
                    content=content,
                    memory_type=str(
                        item.get("memory_type", "NOTE")
                    ).upper(),
                ).memory_type
            except Exception:
                memory_type = MemoryCreate(
                    content=content,
                    memory_type="NOTE",
                ).memory_type

            candidates = memory_store.search(content, limit=5)
            decision = classify_memory(content, candidates)

            if decision.relationship.value == "DUPLICATE":
                duplicates.append(
                    memory_store.get_by_id(
                        decision.related_memory_id
                    )
                )
                continue

            memory = MemoryRecord(
                content=content,
                memory_type=memory_type,
                relationship=decision.relationship,
                related_memory_id=decision.related_memory_id,
                status=(
                    "REVIEW_REQUIRED"
                    if decision.requires_review
                    else "ACTIVE"
                ),
            )

            memory_store.save(memory)
            saved.append(memory.model_dump(mode="json"))

        return {
            "extracted_count": len(memories),
            "saved_count": len(saved),
            "duplicate_count": len(duplicates),
            "saved_memories": saved,
            "duplicates": duplicates,
        }

    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail=(
                f"Lyzr API returned status "
                f"{exc.response.status_code}"
            ),
        ) from exc

    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail="Could not connect to Lyzr API",
        ) from exc

    except (ValueError, TypeError, AttributeError) as exc:
        raise HTTPException(
            status_code=502,
            detail="Could not parse Lyzr's extraction response",
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Failed to save extracted memories",
        ) from exc
