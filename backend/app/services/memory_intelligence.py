
from dataclasses import dataclass
import re

from app.models.memory import MemoryRelationship


@dataclass
class MemoryDecision:
    relationship: MemoryRelationship
    related_memory_id: str | None = None
    requires_review: bool = False


def normalize_text(text: str) -> str:
    """Normalize text for simple duplicate comparisons."""
    text = text.casefold().strip()
    text = re.sub(r"[^\w\s]", " ", text)
    return " ".join(text.split())


def classify_memory(
    content: str,
    existing_memories: list[dict],
) -> MemoryDecision:
    """Classify a statement using conservative rule-based checks."""
    text = normalize_text(content)

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

    # Ignore weak semantic search matches.
    candidates = [
        memory
        for memory in existing_memories
        if float(memory.get("score", 0)) >= 0.78
        and memory.get("id")
        and memory.get("content")
    ]

    # First check for exact or normalized duplicates.
    for memory in candidates:
        old_text = normalize_text(str(memory["content"]))

        if text == old_text:
            return MemoryDecision(
                MemoryRelationship.DUPLICATE,
                str(memory["id"]),
            )

    # Treat highly overlapping text as a possible duplicate.
    new_words = set(text.split())

    if len(new_words) >= 4:
        for memory in candidates:
            old_text = normalize_text(str(memory["content"]))
            old_words = set(old_text.split())

            if not old_words:
                continue

            overlap = len(new_words & old_words) / max(
                len(new_words),
                len(old_words),
            )

            if overlap >= 0.75:
                return MemoryDecision(
                    MemoryRelationship.DUPLICATE,
                    str(memory["id"]),
                )

    # Only consider updates when the statement explicitly signals a change.
    has_update_phrase = any(
        phrase in text for phrase in update_phrases
    )

    if has_update_phrase:
        decision_candidates = [
            memory
            for memory in candidates
            if memory.get("memory_type") == "DECISION"
        ]

        if len(decision_candidates) == 1:
            return MemoryDecision(
                MemoryRelationship.SUPERSEDES,
                str(decision_candidates[0]["id"]),
            )

        return MemoryDecision(
            MemoryRelationship.UNRELATED,
            requires_review=True,
        )

    return MemoryDecision(MemoryRelationship.NEW)
