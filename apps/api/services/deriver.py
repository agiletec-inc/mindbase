"""Derivation pipeline that converts raw conversations into enriched records."""

from __future__ import annotations

from datetime import datetime
from typing import Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from apps.api import crud
from apps.api.models.conversation import RawConversation
from apps.api.ollama_client import ollama_client
from apps.api.schemas.conversation import ConversationCreate, ConversationResponse
from apps.api.services import settings_store
from apps.api.services.classifier import infer_project, infer_topics
from apps.api.services.pipelines import run_post_derivation


def _extract_text_from_content(content: dict) -> Tuple[str, int, str | None]:
    """Flatten conversation content for embedding generation."""
    if "messages" in content:
        messages = content["messages"]
        flattened = [
            str(msg.get("content", "")) for msg in messages if "content" in msg
        ]
        joined = " ".join(flattened)
        raw_content = "\n\n".join(flattened)
        return joined, len(flattened), raw_content
    content_str = str(content)
    return content_str, 0, None


async def process_raw_conversation(
    db: AsyncSession,
    raw_record: RawConversation,
) -> ConversationResponse:
    """Derive a conversation entry from the raw payload."""

    payload = ConversationCreate(**raw_record.payload)
    metadata = dict(payload.metadata or {})

    workspace_path = (
        raw_record.workspace_path
        or payload.workspace
        or payload.content.get("workspace")
        or metadata.get("workspace")
    )
    if workspace_path:
        metadata["workspace_path"] = workspace_path
        metadata.setdefault("workspace", workspace_path)

    text_content, message_count, raw_content = _extract_text_from_content(
        payload.content
    )
    # Embed with the active provider. The vector is stored in
    # conversation_embeddings (keyed by provider/model), not the legacy
    # conversations.embedding column, so providers with different dimensions
    # can coexist.
    provider, model = settings_store.get_active_embedding()
    embedding = await ollama_client.embed(
        text_content or " ", provider=provider, model=model
    )

    project = infer_project(
        metadata=payload.metadata,
        content=payload.content,
        text=text_content,
        explicit=payload.project or metadata.get("project"),
    )
    topics = infer_topics(
        text_content,
        existing=payload.topics or metadata.get("topics"),
    )
    if project:
        metadata["project"] = project
    metadata["topics"] = topics

    conversation = await crud.create_conversation_record(
        db,
        payload,
        raw_record=raw_record,
        workspace_path=workspace_path,
        message_count=message_count,
        raw_content=raw_content,
        project=project,
        topics=topics,
        metadata=metadata,
    )
    await crud.upsert_conversation_embedding(
        db, conversation.id, provider, model, embedding
    )

    raw_record.processed_at = datetime.utcnow()
    raw_record.processing_error = None

    await run_post_derivation(conversation)

    return ConversationResponse(
        id=conversation.id,
        raw_id=conversation.raw_id,
        source=conversation.source,
        source_conversation_id=conversation.source_conversation_id,
        title=conversation.title,
        content=conversation.content,
        metadata=conversation.conv_metadata or {},
        message_count=conversation.message_count,
        project=conversation.project,
        topics=conversation.topics or [],
        workspace_path=conversation.workspace_path,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
    )
