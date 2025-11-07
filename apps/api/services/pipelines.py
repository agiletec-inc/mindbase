"""Pipeline hooks executed after conversations are derived."""

from __future__ import annotations

import logging

from app.schemas.conversation import ConversationResponse

logger = logging.getLogger(__name__)


async def run_post_derivation(conversation: ConversationResponse) -> None:
    """Hook for future pipeline fan-out."""
    logger.debug("Post-derivation hook executed", extra={"conversation_id": str(conversation.id)})
