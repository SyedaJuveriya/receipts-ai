
from dataclasses import dataclass

from app.models.memory import MemoryRelationship


@dataclass
class MemoryDecision:
    relationship: MemoryRelationship
    related_memory_id: str | None = None
    requires_review: bool = False


def classify_memory(
    content: str,
    existing_memories: list[dict],
) -> MemoryDecision:
    """Classify a statement using conservative rule-based checks."""
    text = content.casefold().strip()

    if not existing_memories:
        return MemoryDecision(MemoryRelationship.NEW)

    update_phrases = (
        "actually",
        "instead",
        "change to",
        "switch to",
        "replace with",
        "no longer",
        "we changed",
        "update that",
    )

    for memory in existing_memories:
        old_content = str(memory.get("content", "")).casefold().strip()
        old_id = memory.get("id")

        if not old_id or not old_content:
            continue

        if text == old_content:
            return MemoryDecision(
                MemoryRelationship.DUPLICATE,
                str(old_id),
            )

        if any(phrase in text for phrase in update_phrases):
            if memory.get("memory_type") == "DECISION":
                return MemoryDecision(
                    MemoryRelationship.SUPERSEDES,
                    str(old_id),
                )

            return MemoryDecision(
                MemoryRelationship.UNRELATED,
                str(old_id),
                requires_review=True,
            )

    return MemoryDecision(MemoryRelationship.NEW)
