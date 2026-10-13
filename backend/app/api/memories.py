import json
import re
from difflib import SequenceMatcher
from typing import Any

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


def normalize(text: str) -> str:
    text = str(text).casefold()
    text = re.sub(r"[^a-z0-9+#.\s]", " ", text)
    return " ".join(text.split())


CHANGE_WORDS = {
    "actually", "switch", "switched", "switches", "switching", "to",
    "change", "changed", "changes", "the", "decision", "use", "using",
    "replace", "replaced", "replacing", "it", "with", "instead", "we",
    "decided", "will", "for", "our", "a", "an", "no", "longer",
    "update", "that", "my", "i", "from", "rather", "than", "old", "new",
    "prefer", "prefers", "preferred", "choose", "chose", "choosing",
    "want", "wants", "wanted", "plan", "planned", "planning",
}

CONTEXT_STOPWORDS = CHANGE_WORDS | {
    "every", "each", "morning", "evening", "afternoon", "night",
    "daily", "weekly", "currently", "previously",
}

CHANGE_PHRASES = (
    "actually", "instead", "rather than", "switch to", "switched to",
    "change to", "changed to", "changed decision", "change my decision",
    "changed my decision", "replace with", "replaced with", "no longer",
    "we changed", "update that",
)


def has_explicit_change(content: str) -> bool:
    text = content.casefold()
    return any(phrase in text for phrase in CHANGE_PHRASES)


def meaningful_tokens(content: str) -> set[str]:
    return {
        token
        for token in normalize(content).split()
        if token not in CONTEXT_STOPWORDS and len(token) > 1
    }


def replacement_clause(content: str) -> str | None:
    match = re.search(
        r"\b(?:instead\s+of|rather\s+than)\s+(.+?)(?:[.!?]|$)",
        content,
        flags=re.IGNORECASE,
    )
    return match.group(1).strip() if match else None


def current_decision_clause(content: str) -> str:
    """Return the newly chosen part, omitting change-introduction wording."""
    text = content.strip()
    text = re.sub(
        r"^\s*(?:i\s+)?(?:have\s+)?(?:changed\s+(?:my\s+)?decision|"
        r"changed\s+my\s+decision|changed\s+decision|"
        r"decided|i\s+decided|we\s+decided|actually|"
        r"switched\s+to|switch\s+to|changed\s+to|"
        r"i\s+will|we\s+will|will)\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.split(r"\b(?:instead\s+of|rather\s+than)\b", text, maxsplit=1, flags=re.I)[0]
    return normalize(text).strip(" .")


def same_current_decision(first: str, second: str) -> bool:
    first_clause = current_decision_clause(first)
    second_clause = current_decision_clause(second)

    if first_clause and first_clause == second_clause:
        return True

    first_tokens = meaningful_tokens(first_clause)
    second_tokens = meaningful_tokens(second_clause)
    if not first_tokens or not second_tokens:
        return False

    overlap = len(first_tokens & second_tokens)
    smaller = min(len(first_tokens), len(second_tokens))
    union = len(first_tokens | second_tokens)
    return (
        overlap >= 3
        and overlap / smaller >= 0.90
        and overlap / union >= 0.75
    )


def is_duplicate(
    content: str,
    memory_type: MemoryType,
    candidates: list[dict],
) -> dict | None:
    new_text = normalize(content)
    new_tokens = meaningful_tokens(content)

    for candidate in candidates:
        if candidate.get("memory_type") != memory_type.value:
            continue
        if candidate.get("status", MemoryStatus.ACTIVE.value) not in {
            MemoryStatus.ACTIVE.value,
            "REVIEW_REQUIRED",
        }:
            continue

        candidate_id = candidate.get("id")
        old_content = str(candidate.get("content", ""))
        if not candidate_id or not old_content:
            continue

        old_text = normalize(old_content)
        if new_text == old_text:
            return candidate

        # Decision entries often differ only in introductory wording.
        if memory_type == MemoryType.DECISION and same_current_decision(content, old_content):
            return candidate

        # Conservative lexical fallback for non-identical wording.
        old_tokens = meaningful_tokens(old_content)
        if new_tokens and old_tokens:
            overlap = len(new_tokens & old_tokens)
            smaller = min(len(new_tokens), len(old_tokens))
            union = len(new_tokens | old_tokens)
            if (
                overlap >= 4
                and overlap / smaller >= 0.92
                and overlap / union >= 0.80
            ):
                return candidate

        # Catch near-identical sentences without treating broad semantic
        # similarity alone as a duplicate.
        if SequenceMatcher(None, new_text, old_text).ratio() >= 0.94:
            return candidate

    return None


# Choice-based changes, e.g. PostgreSQL -> MySQL.
CHANGE_PATTERNS = (
    r"\b(?:actually\s*,?\s*)?switched?\s+to\s+([a-z][a-z0-9+#.-]*)\b",
    r"\bchanged?\s+(?:the\s+)?decision\s+to\s+use\s+([a-z][a-z0-9+#.-]*)\b",
    r"\bchanged?\s+decision\s+to\s+use\s+([a-z][a-z0-9+#.-]*)\b",
    r"\breplaced?\s+(?:it\s+)?with\s+([a-z][a-z0-9+#.-]*)\b",
    r"\buse\s+([a-z][a-z0-9+#.-]*)\s+instead\b",
    r"\b(?:we\s+)?decided\s+to\s+use\s+([a-z][a-z0-9+#.-]*)\b",
    r"\b(?:we\s+)?will\s+use\s+([a-z][a-z0-9+#.-]*)\b",
)


def extract_decision_choice(content: str) -> str | None:
    for pattern in CHANGE_PATTERNS:
        match = re.search(pattern, content.strip(), flags=re.IGNORECASE)
        if match:
            return match.group(1).casefold()
    return None


def decision_context(content: str, choice: str) -> set[str]:
    tokens = set(normalize(content).split())
    tokens.discard(choice)
    return tokens - CHANGE_WORDS


def same_decision_context(new_content: str, old_content: str) -> bool:
    old_clause = replacement_clause(new_content)
    if old_clause:
        # Compare the explicitly replaced routine with the old decision's chosen
        # routine, not the whole sentence (which may mention two routines).
        old_current_tokens = meaningful_tokens(current_decision_clause(old_content))
        clause_tokens = meaningful_tokens(old_clause)
        shared = old_current_tokens & clause_tokens
        if (
            len(shared) >= 2
            and len(shared) / max(len(old_current_tokens), 1) >= 0.60
        ):
            return True

    new_choice = extract_decision_choice(new_content)
    old_choice = extract_decision_choice(old_content)

    if not old_choice:
        match = re.search(
            r"\b(?:use|using)\s+([a-z][a-z0-9+#.-]*)\b",
            old_content,
            flags=re.IGNORECASE,
        )
        if match:
            old_choice = match.group(1).casefold()

    if not new_choice or not old_choice or new_choice == old_choice:
        return False

    shared_context = decision_context(new_content, new_choice) & decision_context(
        old_content, old_choice
    )
    return len(shared_context) >= 2


def find_previous_decisions(content: str) -> list[dict]:
    if not has_explicit_change(content):
        return []

    # Search both the full statement and the old routine named after
    # "instead of"; Qdrant can rank the full sentence below relevant records.
    queries = [content]
    old_clause = replacement_clause(content)
    if old_clause:
        queries.append(old_clause)

    candidates_by_id: dict[str, dict] = {}
    for query in queries:
        for item in memory_store.search(query, limit=20):
            memory_id = item.get("id")
            if memory_id:
                candidates_by_id[str(memory_id)] = item

    matches: list[dict] = []
    for item in candidates_by_id.values():
        if item.get("memory_type") != MemoryType.DECISION.value:
            continue
        if item.get("status", MemoryStatus.ACTIVE.value) != MemoryStatus.ACTIVE.value:
            continue
        if same_decision_context(content, str(item.get("content", ""))):
            matches.append(item)

    return sorted(matches, key=lambda item: float(item.get("score", 0)), reverse=True)


def supersede_decisions(
    old_memories: list[dict],
    new_content: str,
) -> tuple[MemoryRecord, list[dict]]:
    old_records: list[dict] = []

    for item in old_memories:
        record = memory_store.get_by_id(str(item["id"]))
        if not record:
            continue
        if record.get("status", MemoryStatus.ACTIVE.value) != MemoryStatus.ACTIVE.value:
            continue

        old_record = MemoryRecord.model_validate(record)
        old_record.status = MemoryStatus.SUPERSEDED
        memory_store.update(old_record)
        old_records.append(
            {
                "id": old_record.id,
                "content": old_record.content,
                "status": MemoryStatus.SUPERSEDED.value,
            }
        )

    new_record = MemoryRecord(
        content=new_content,
        memory_type=MemoryType.DECISION,
        status=MemoryStatus.ACTIVE,
        relationship=MemoryRelationship.SUPERSEDES if old_records else MemoryRelationship.UNRELATED,
        related_memory_id=old_records[0]["id"] if old_records else None,
    )
    memory_store.save(new_record)
    return new_record, old_records


def find_duplicate(content: str, memory_type: MemoryType) -> dict | None:
    candidates = memory_store.search(content, limit=20)
    return is_duplicate(content, memory_type, candidates)


@router.post("")
def create_memory(data: MemoryCreate):
    try:
        prior = (
            find_previous_decisions(data.content)
            if data.memory_type == MemoryType.DECISION
            else []
        )
        if prior:
            # An explicit change takes precedence over broad similarity matches.
            # If it has no prior choice to replace, fall through to duplicate detection.
            new_record, old_records = supersede_decisions(prior, data.content)
            return {
                "memory": new_record.model_dump(mode="json"),
                "relationship": MemoryRelationship.SUPERSEDES.value,
                "superseded_memories": old_records,
                "requires_review": False,
            }

        duplicate = find_duplicate(data.content, data.memory_type)
        if duplicate:
            return {
                "message": "Duplicate memory detected",
                "memory": memory_store.get_by_id(str(duplicate["id"])),
                "relationship": MemoryRelationship.DUPLICATE.value,
            }

        memory = MemoryRecord(
            content=data.content,
            memory_type=data.memory_type,
            due_at=data.due_at,
            status=MemoryStatus.ACTIVE,
        )
        memory_store.save(memory)
        return {
            "memory": memory.model_dump(mode="json"),
            "relationship": memory.relationship.value,
            "requires_review": False,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to process memory") from exc


@router.get("/search")
def search_memories(q: str, limit: int = 5):
    if not q.strip():
        raise HTTPException(status_code=400, detail="Search query cannot be empty")
    if not 1 <= limit <= 20:
        raise HTTPException(status_code=400, detail="Limit must be between 1 and 20")
    try:
        return {"results": memory_store.search(q, limit)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to search memories") from exc


@router.post("/extract")
async def extract_memories_with_lyzr(data: LyzrExtractRequest):
    try:
        result = await lyzr_service.extract_memories(data.message)
        memories = parse_lyzr_response(result)

        saved: list[dict] = []
        duplicates: list[dict] = []
        superseded: list[dict] = []
        review_required: list[str] = []

        for item in memories:
            content = str(item.get("content", "")).strip()
            if not content:
                continue

            try:
                memory_type = MemoryType(str(item.get("memory_type", "NOTE")).upper())
            except ValueError:
                memory_type = MemoryType.NOTE

            # An explicit decision change must be evaluated before broad
            # duplicate similarity, otherwise a new schedule can be mistaken
            # for an existing decision and never supersede it.
            prior = (
                find_previous_decisions(content)
                if memory_type == MemoryType.DECISION
                else []
            )
            if prior:
                new_record, old_records = supersede_decisions(prior, content)
                saved.append(new_record.model_dump(mode="json"))
                superseded.extend(old_records)
                continue

            candidates = memory_store.search(content, limit=20)
            duplicate = is_duplicate(content, memory_type, candidates)
            if duplicate:
                existing = memory_store.get_by_id(str(duplicate["id"]))
                if existing:
                    duplicates.append(existing)
                continue

            memory = MemoryRecord(
                content=content,
                memory_type=memory_type,
                status=MemoryStatus.ACTIVE,
            )
            memory_store.save(memory)
            saved.append(memory.model_dump(mode="json"))

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

@router.get("/followups")
def get_followups(limit: int = 10):
    if not 1 <= limit <= 20:
        raise HTTPException(status_code=400, detail="Limit must be between 1 and 20")

    wanted_types = {MemoryType.DECISION.value, MemoryType.COMMITMENT.value}
    seen: dict[str, dict] = {}

    for query in ("commitment to do", "decided to", "plan will", "study", "meeting", "task deadline"):
        try:
            results = memory_store.search(query, limit=20)
        except Exception:
            continue
        for item in results:
            memory_id = item.get("id")
            if not memory_id:
                continue
            if item.get("memory_type") not in wanted_types:
                continue
            if item.get("status", MemoryStatus.ACTIVE.value) != MemoryStatus.ACTIVE.value:
                continue
            seen[str(memory_id)] = item

    items = sorted(
        seen.values(),
        key=lambda m: str(m.get("created_at", "")),
        reverse=True,
    )[:limit]

    followups = [
        {
            "id": m.get("id"),
            "content": m.get("content"),
            "memory_type": m.get("memory_type"),
            "created_at": m.get("created_at"),
            "due_at": m.get("due_at"),
            "nudge": f"You said: \"{m.get('content')}\" - still pending?",
        }
        for m in items
    ]
    return {"count": len(followups), "followups": followups}