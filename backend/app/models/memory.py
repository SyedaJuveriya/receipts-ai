from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field


class MemoryType(str, Enum):
    COMMITMENT = "COMMITMENT"
    DECISION = "DECISION"
    NOTE = "NOTE"


class MemoryStatus(str, Enum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    SUPERSEDED = "SUPERSEDED"
    CONTRADICTED = "CONTRADICTED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"

class MemoryRelationship(str, Enum):
    NEW = "NEW"
    DUPLICATE = "DUPLICATE"
    UPDATE = "UPDATE"
    SUPERSEDES = "SUPERSEDES"
    CONTRADICTS = "CONTRADICTS"
    UNRELATED = "UNRELATED"


class MemoryCreate(BaseModel):
    content: str = Field(min_length=1, max_length=5000)
    memory_type: MemoryType = MemoryType.NOTE
    due_at: datetime | None = None


class MemoryRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    content: str
    memory_type: MemoryType
    status: MemoryStatus = MemoryStatus.ACTIVE
    relationship: MemoryRelationship = MemoryRelationship.NEW
    related_memory_id: str | None = None
    due_at: datetime | None = None
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )