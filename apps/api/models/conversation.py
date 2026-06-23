"""SQLAlchemy models for MindBase conversations."""

from __future__ import annotations

import os
from datetime import datetime
import uuid

from pgvector.sqlalchemy import Vector

EMBEDDING_DIMENSIONS = int(os.getenv("EMBEDDING_DIMENSIONS", "3072"))
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

from apps.api.database import Base


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
    inserted_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
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
    raw_id = Column(
        UUID(as_uuid=True), ForeignKey("raw_conversations.id", ondelete="SET NULL")
    )

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

    # Embedding (OpenAI text-embedding-3-large = 3072 dimensions, Ollama fallback)
    embedding = Column(Vector(EMBEDDING_DIMENSIONS))

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
        UniqueConstraint(
            "source", "source_conversation_id", name="unique_source_conversation"
        ),
    )

    def __repr__(self) -> str:  # pragma: no cover - repr helper
        return f"<Conversation(id={self.id}, source={self.source}, title={self.title})>"


# Dimension-bucket columns on ConversationEmbedding, keyed by vector length.
# A row fills exactly one of these (the one matching its provider/model dim).
EMBEDDING_DIM_COLUMNS = {
    768: "vec_768",
    1024: "vec_1024",
    3072: "vec_3072",
    4096: "vec_4096",
}


class ConversationEmbedding(Base):
    """One embedding per (conversation, provider, model).

    Vectors from different models have different dimensions and are not
    comparable, so each row stores its vector in the dimension-bucket column
    matching its length. This lets OpenAI, bge-m3, qwen3-embedding, etc. coexist
    for the same conversation so providers can be compared. See migration
    20260606000000_conversation_embeddings.sql.
    """

    __tablename__ = "conversation_embeddings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    provider = Column(String, nullable=False)
    model = Column(String, nullable=False)
    dim = Column(Integer, nullable=False)
    vec_768 = Column(Vector(768))
    vec_1024 = Column(Vector(1024))
    vec_3072 = Column(Vector(3072))
    vec_4096 = Column(Vector(4096))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint(
            "conversation_id",
            "provider",
            "model",
            name="conversation_embeddings_conversation_id_provider_model_key",
        ),
    )

    def __repr__(self) -> str:  # pragma: no cover - repr helper
        return (
            f"<ConversationEmbedding(conversation_id={self.conversation_id}, "
            f"provider={self.provider}, model={self.model}, dim={self.dim})>"
        )
