"""Simple async worker that processes raw conversations into derived records."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import get_settings
from app.models.conversation import RawConversation
from app.services.deriver import process_raw_conversation

logging.basicConfig(
    level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s"
)
logger = logging.getLogger(__name__)


async def derive_loop() -> None:
    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL, future=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    batch_size = settings.DERIVER_BATCH_SIZE or 5
    idle_seconds = settings.DERIVER_IDLE_SECONDS or 5
    max_retries = settings.DERIVER_MAX_RETRIES or 3

    logger.info(
        "Raw derivation worker started (batch=%s idle=%ss retries=%s)",
        batch_size,
        idle_seconds,
        max_retries,
    )
    try:
        while True:
            processed_any = False
            async with session_factory() as session:
                result = await session.execute(
                    select(RawConversation)
                    .where(RawConversation.processed_at.is_(None))
                    .order_by(RawConversation.inserted_at)
                    .limit(batch_size)
                )
                batch = result.scalars().all()

                if not batch:
                    await asyncio.sleep(idle_seconds)
                    continue

                for raw in batch:
                    try:
                        await process_raw_conversation(session, raw)
                        processed_any = True
                        await session.commit()
                        logger.info("Derived raw conversation %s", raw.id)
                    except Exception as exc:  # pragma: no cover - worker log
                        logger.exception("Failed to derive raw conversation %s", raw.id)
                        raw.retry_count = (raw.retry_count or 0) + 1
                        if raw.retry_count >= max_retries:
                            raw.processing_error = str(exc)
                            raw.processed_at = datetime.utcnow()
                            logger.error(
                                "Giving up on raw conversation %s after %s retries",
                                raw.id,
                                raw.retry_count,
                            )
                        else:
                            raw.processing_error = str(exc)
                        await session.commit()

            if not processed_any:
                await asyncio.sleep(idle_seconds)
            else:
                await asyncio.sleep(0)
    finally:
        await engine.dispose()


def main() -> None:
    asyncio.run(derive_loop())


if __name__ == "__main__":
    main()
