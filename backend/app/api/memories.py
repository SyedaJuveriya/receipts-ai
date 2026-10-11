
import json
import httpx

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.models.memory import (
    MemoryCreate,
    MemoryRecord,
    MemoryRelationship,
    MemoryStatus,
    MemoryType,
)
from app.services.lyzr_service import lyzr_service
from app.services.memory_intelligence import classify_memory
from app.services.memory_store import MemoryStore

router = APIRouter(prefix="/memories", tags=["memories"])
memory_store = MemoryStore()


class LyzrExtractRequest(BaseModel):
    message: str = Field(min_length=1, max_length=5000)


def parse_lyzr_response(result: dict) -> list[dict]:
    raw = result.get("response", result)

    if isinstance(raw, str):
        raw = json.loads(raw)

    if not isinstance(raw, dict):
        raise ValueError("Unexpected Lyzr response format")

    memories = raw.get("memories", [])
    if not isinstance(memories, list):
        raise ValueError("Expected a memories list")

    return [item for item in memories if isinstance(item, dict)]


def has_explicit_change(content: str) -> bool:
    text = content.casefold()
    phrases = (
        "actually",
        "instead",
        "change to",
        "switch to",
        "replace with",
        "no longer",
        "we changed",
        "update that",
        "changed decision",
        "switched to",
    )
    return any(phrase in text for phrase in phrases)


def find_previous_decision(content: str) -> dict | None:
    candidates = memory_store.search(content, limit=20)

    new_text = content.casefold()
    known_choices = ("mysql", "postgresql", "sqlite", "mongodb")
    new_choice = next(
        (choice for choice in known_choices if choice in new_text),
        None,
    )

    if not new_choice:
        return None

    conflicting = [
        item
        for item in candidates
        if item.get("id")
        and item.get("memory_type") == MemoryType.DECISION.value
        and item.get("status", MemoryStatus.ACTIVE.value)
        == MemoryStatus.ACTIVE.value
        and any(
            choice in str(item.get("content", "")).casefold()
            for choice in known_choices
            if choice != new_choice
        )
    ]

    if not conflicting:
        return None

    return max(
        conflicting,
        key=lambda item: float(item.get("score", 0)),
    )


@router.post("")
def create_memory(data: MemoryCreate):
    try:
        candidates = memory_store.search(data.content, limit=5)
        decision = classify_memory(data.content, candidates)

        if decision.relationship == MemoryRelationship.DUPLICATE:
            return {
                "message": "Duplicate memory detected",
                "memory": memory_store.get_by_id(
                    decision.related_memory_id
                ),
                "relationship": decision.relationship.value,
            }

        memory = MemoryRecord(
            content=data.content,
            memory_type=data.memory_type,
            due_at=data.due_at,
            relationship=decision.relationship,
            related_memory_id=decision.related_memory_id,
            status=(
                MemoryStatus.REVIEW_REQUIRED
                if decision.requires_review
                else MemoryStatus.ACTIVE
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
        memories = parse_lyzr_response(result)

        saved = []
        duplicates = []
        superseded = []
        review_required = []

        for item in memories:
            content = str(item.get("content", "")).strip()
            if not content:
                continue

            try:
                memory_type = MemoryType(
                    str(item.get("memory_type", "NOTE")).upper()
                )
            except ValueError:
                memory_type = MemoryType.NOTE

            # IMPORTANT: check explicit decision changes BEFORE duplicate
            # detection. Otherwise an existing replacement can hide the
            # conflicting decision that needs to be superseded.
            prior = None
            if (
                memory_type == MemoryType.DECISION
                and has_explicit_change(content)
            ):
                prior = find_previous_decision(content)

            if prior:
                old_memory = memory_store.get_by_id(str(prior["id"]))

                if old_memory:
                    old_record = MemoryRecord.model_validate(old_memory)
                    old_record.status = MemoryStatus.SUPERSEDED
                    memory_store.update(old_record)

                    superseded.append({
                        "id": old_record.id,
                        "content": old_record.content,
                        "status": old_record.status.value,
                    })

                    memory = MemoryRecord(
                        content=content,
                        memory_type=memory_type,
                        relationship=MemoryRelationship.SUPERSEDES,
                        related_memory_id=old_record.id,
                        status=MemoryStatus.ACTIVE,
                    )
                    memory_store.save(memory)
                    saved.append(memory.model_dump(mode="json"))
                    continue

            candidates = memory_store.search(content, limit=10)
            decision = classify_memory(content, candidates)

            if decision.relationship == MemoryRelationship.DUPLICATE:
                duplicates.append(
                    memory_store.get_by_id(decision.related_memory_id)
                )
                continue

            status = (
                MemoryStatus.REVIEW_REQUIRED
                if decision.requires_review
                else MemoryStatus.ACTIVE
            )

            memory = MemoryRecord(
                content=content,
                memory_type=memory_type,
                relationship=decision.relationship,
                related_memory_id=decision.related_memory_id,
                status=status,
            )
            memory_store.save(memory)
            saved.append(memory.model_dump(mode="json"))

            if status == MemoryStatus.REVIEW_REQUIRED:
                review_required.append(memory.id)

        return {
            "extracted_count": len(memories),
            "saved_count": len(saved),
            "duplicate_count": len(duplicates),
            "superseded_count": len(superseded),
            "review_required_count": len(review_required),
            "saved_memories": saved,
            "duplicates": duplicates,
            "superseded_memories": superseded,
            "review_required_ids": review_required,
        }

    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Lyzr API returned status {exc.response.status_code}",
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
