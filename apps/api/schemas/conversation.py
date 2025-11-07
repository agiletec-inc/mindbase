"""Conversation Pydantic schemas"""

from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID
from typing import Optional, Any, List, Literal


class ConversationCreate(BaseModel):
    """Schema for creating a conversation"""

    source: str = Field(..., description="Source of conversation (claude-code, chatgpt, etc.)")
    source_conversation_id: Optional[str] = Field(None, description="Original conversation ID from source")
    workspace: Optional[str] = Field(
        None,
        description="Path to the workspace/monorepo root where this conversation originated",
    )
    title: Optional[str] = Field(None, description="Conversation title")
    content: dict[str, Any] = Field(..., description="Full conversation content (JSONB)")
    metadata: Optional[dict[str, Any]] = Field(default_factory=dict, description="Custom metadata")
    source_created_at: Optional[datetime] = Field(None, description="Original creation time")
    project: Optional[str] = Field(None, description="Detected or assigned project name")
    topics: Optional[List[str]] = Field(
        default=None,
        description="List of detected topics associated with the conversation"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "source": "claude-code",
                "workspace": "/Users/alice/github/mindbase",
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
    raw_id: Optional[UUID]
    source: str
    source_conversation_id: Optional[str]
    title: Optional[str]
    content: dict[str, Any]
    metadata: dict[str, Any] = Field(default_factory=dict)
    message_count: int
    project: Optional[str]
    topics: List[str] = Field(default_factory=list)
    workspace_path: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ConversationQueuedResponse(BaseModel):
    """Schema returned when derivation is queued."""

    raw_id: UUID
    status: Literal["queued"] = "queued"


class CollectorConfig(BaseModel):
    id: str
    label: str
    workspace: Optional[str] = None


class PipelineConfig(BaseModel):
    id: str
    label: str


class AppSettings(BaseModel):
    apiBaseUrl: str = Field("http://localhost:18002", description="MindBase API URL")
    workspaceRoot: str = Field("~/github/mindbase", description="Default workspace")
    repoRoot: str = Field("~/github/mindbase", description="Path where make commands run")
    refreshIntervalMs: int = Field(15000, description="Menubar poll interval in milliseconds")
    collectors: List[CollectorConfig] = Field(default_factory=list)
    pipelines: List[PipelineConfig] = Field(default_factory=list)


class CommandResult(BaseModel):
    """Represents the outcome of a control command."""

    action: str
    returncode: int
    stdout: str
    stderr: str


class SearchQuery(BaseModel):
    """Schema for semantic search query"""

    query: str = Field(..., description="Search query text", min_length=1)
    limit: int = Field(10, description="Maximum number of results", ge=1, le=100)
    threshold: float = Field(0.8, description="Similarity threshold", ge=0.0, le=1.0)
    source: Optional[str] = Field(None, description="Filter by source")
    project: Optional[str] = Field(None, description="Filter by project identifier")
    topic: Optional[str] = Field(None, description="Filter by topic tag")
    workspace_path: Optional[str] = Field(None, description="Filter by workspace path")

    class Config:
        json_schema_extra = {
            "example": {
                "query": "PM Agent autonomous investigation",
                "limit": 10,
                "threshold": 0.8,
                "source": "claude-code",
                "project": "superclaude",
                "topic": "Testing Strategy",
                "workspace_path": "/Users/alice/github/mindbase",
            }
        }


class SearchResult(BaseModel):
    """Schema for search result"""

    id: UUID
    raw_id: Optional[UUID]
    title: Optional[str]
    source: str
    similarity: float
    project: Optional[str]
    topics: List[str] = Field(default_factory=list)
    workspace_path: Optional[str]
    created_at: datetime
    content_preview: str = Field(..., description="First 200 chars of content")

    class Config:
        from_attributes = True
