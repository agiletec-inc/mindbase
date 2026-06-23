"""CRUD operations"""

from apps.api.crud.conversation import (
    create_conversation_record,
    create_raw_conversation,
    get_conversation,
    list_conversations,
)
from apps.api.crud.search import search_conversations
from apps.api.crud.embeddings import (
    column_for_dim,
    count_conversations_missing_embedding,
    list_conversations_missing_embedding,
    search_conversation_embeddings,
    upsert_conversation_embedding,
)

__all__ = [
    "create_raw_conversation",
    "create_conversation_record",
    "get_conversation",
    "list_conversations",
    "search_conversations",
    "column_for_dim",
    "count_conversations_missing_embedding",
    "list_conversations_missing_embedding",
    "search_conversation_embeddings",
    "upsert_conversation_embedding",
]
