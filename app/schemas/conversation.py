"""Conversation Pydantic schemas"""

from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID
from typing import Optional, Any


class ConversationCreate(BaseModel):
    """Schema for creating a conversation"""

    source: str = Field(..., description="Source of conversation (claude-code, chatgpt, etc.)")
    source_conversation_id: Optional[str] = Field(None, description="Original conversation ID from source")
    title: Optional[str] = Field(None, description="Conversation title")
    content: dict[str, Any] = Field(..., description="Full conversation content (JSONB)")
    metadata: Optional[dict[str, Any]] = Field(default_factory=dict, description="Custom metadata")
    source_created_at: Optional[datetime] = Field(None, description="Original creation time")

    class Config:
        json_schema_extra = {
            "example": {
                "source": "claude-code",
                "title": "SuperClaude PM Agent Enhancement",
                "content": {
                    "messages": [
                        {"role": "user", "content": "Implement PM Agent autonomous features"},
                        {"role": "assistant", "content": "I'll implement Phase 0, 1, 2..."}
                    ]
                },
                "metadata": {"project": "superclaude", "tags": ["pm-agent", "autonomous"]}
            }
        }


class ConversationResponse(BaseModel):
    """Schema for conversation response"""

    id: UUID
    source: str
    source_conversation_id: Optional[str]
    title: Optional[str]
    content: dict[str, Any]
    metadata: dict[str, Any]
    message_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SearchQuery(BaseModel):
    """Schema for semantic search query"""

    query: str = Field(..., description="Search query text", min_length=1)
    limit: int = Field(10, description="Maximum number of results", ge=1, le=100)
    threshold: float = Field(0.8, description="Similarity threshold", ge=0.0, le=1.0)
    source: Optional[str] = Field(None, description="Filter by source")

    class Config:
        json_schema_extra = {
            "example": {
                "query": "PM Agent autonomous investigation",
                "limit": 10,
                "threshold": 0.8,
                "source": "claude-code"
            }
        }


class SearchResult(BaseModel):
    """Schema for search result"""

    id: UUID
    title: Optional[str]
    source: str
    similarity: float
    created_at: datetime
    content_preview: str = Field(..., description="First 200 chars of content")

    class Config:
        from_attributes = True
