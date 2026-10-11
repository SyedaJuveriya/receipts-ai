
from dataclasses import dataclass
import re

from app.models.memory import MemoryRelationship


@dataclass
class MemoryDecision:
    relationship: MemoryRelationship
    related_memory_id: str | None = None
    requires_review: bool = False


def normalize_text(text: str) -> str:
    """Normalize text for duplicate comparison."""
    text = text.casefold().strip()
    text = re.sub(r"[^\w\s]", " ", text)
    return " ".join(text.split())


def classify_memory(
    content: str,
    existing_memories: list[dict],
) -> MemoryDecision:
    """Classify memories using conservative text and similarity checks."""
    text = normalize_text(content)

    if not existing_memories:
        return MemoryDecision(MemoryRelationship.NEW)

    candidates = [
        memory
        for memory in existing_memories
        if memory.get("id") and memory.get("content")
    ]

    # Detect exact normalized duplicates first.
    for memory in candidates:
        if text == normalize_text(str(memory["content"])):
            return MemoryDecision(
                MemoryRelationship.DUPLICATE,
                str(memory["id"]),
            )

    # Detect close textual duplicates among strong semantic matches.
    new_words = set(text.split())

    if len(new_words) >= 4:
        for memory in candidates:
            score = float(memory.get("score", 0))
            if score < 0.78:
                continue

            old_words = set(
                normalize_text(str(memory["content"])).split()
            )
            if not old_words:
                continue

            overlap = len(new_words & old_words) / max(
                len(new_words), len(old_words)
            )

            if overlap >= 0.75:
                return MemoryDecision(
                    MemoryRelationship.DUPLICATE,
                    str(memory["id"]),
                )

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

    if any(phrase in text for phrase in update_phrases):
        decision_candidates = [
            memory
            for memory in candidates
            if memory.get("memory_type") == "DECISION"
            and float(memory.get("score", 0)) >= 0.50
            and memory.get("status", "ACTIVE") == "ACTIVE"
        ]

        # Qdrant returns results by similarity, highest score first.
        # Use the strongest candidate rather than refusing every update
        # when older duplicate decisions exist.
        if decision_candidates:
            best_match = max(
                decision_candidates,
                key=lambda memory: float(memory.get("score", 0)),
            )
            return MemoryDecision(
                MemoryRelationship.SUPERSEDES,
                str(best_match["id"]),
            )

        return MemoryDecision(
            MemoryRelationship.UNRELATED,
            requires_review=True,
        )

    return MemoryDecision(MemoryRelationship.NEW)
