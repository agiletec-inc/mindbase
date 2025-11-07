"""SQLAlchemy models for MindBase conversations."""

from __future__ import annotations

from datetime import datetime
import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    ARRAY,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.database import Base


class RawConversation(Base):
    """Append-only storage for raw conversation payloads."""

    __tablename__ = "raw_conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source = Column(String, nullable=False)
    source_conversation_id = Column(String)
    workspace_path = Column(Text)
    payload = Column(JSONB, nullable=False)
    raw_metadata = Column("metadata", JSONB, nullable=False, default=dict)
    captured_at = Column(DateTime(timezone=True))
    inserted_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    processed_at = Column(DateTime(timezone=True))
    processing_error = Column(Text)
    retry_count = Column(Integer, default=0)

    conversations = relationship(
        "Conversation",
        back_populates="raw",
        passive_deletes=True,
    )

    def __repr__(self) -> str:  # pragma: no cover - repr helper
        return f"<RawConversation(id={self.id}, source={self.source})>"


class Conversation(Base):
    """Derived conversation record enriched with embeddings and metadata."""

    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    raw_id = Column(UUID(as_uuid=True), ForeignKey("raw_conversations.id", ondelete="SET NULL"))

    # Source information
    source = Column(String, nullable=False)
    source_conversation_id = Column(String)
    workspace_path = Column(Text)

    # Content
    title = Column(String)
    content = Column(JSONB, nullable=False)
    raw_content = Column(Text)

    # Metadata
    conv_metadata = Column("metadata", JSONB, default=dict)
    participant_count = Column(Integer, default=2)
    message_count = Column(Integer, default=0)

    # Embedding (qwen3-embedding:8b)
    embedding = Column(Vector(4096))

    # Derived metadata
    project = Column(String)
    topics = Column(ARRAY(String), default=list)

    # Timestamps
    source_created_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    raw = relationship(
        "RawConversation",
        back_populates="conversations",
    )

    __table_args__ = (
        UniqueConstraint("source", "source_conversation_id", name="unique_source_conversation"),
    )

    def __repr__(self) -> str:  # pragma: no cover - repr helper
        return f"<Conversation(id={self.id}, source={self.source}, title={self.title})>"
