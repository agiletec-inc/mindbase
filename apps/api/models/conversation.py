"""Conversation SQLAlchemy model"""

from sqlalchemy import Column, String, Integer, DateTime, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from pgvector.sqlalchemy import Vector
from datetime import datetime
import uuid

from app.database import Base


class Conversation(Base):
    """Conversation model for storing AI conversations"""

    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Source information
    source = Column(
        String,
        nullable=False,
    )
    source_conversation_id = Column(String)

    # Content
    title = Column(String)
    content = Column(JSONB, nullable=False)
    raw_content = Column(Text)

    # Metadata (renamed to avoid SQLAlchemy reserved name)
    conv_metadata = Column("metadata", JSONB, default=dict)
    participant_count = Column(Integer, default=2)
    message_count = Column(Integer, default=0)

    # Vector embedding (qwen3-embedding:8b = 4096 dimensions)
    embedding = Column(Vector(4096))

    # Derived metadata
    project = Column(String)
    topics = Column(ARRAY(String), default=list)

    # Timestamps
    source_created_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("source", "source_conversation_id", name="unique_source_conversation"),
    )

    def __repr__(self):
        return f"<Conversation(id={self.id}, source={self.source}, title={self.title})>"
