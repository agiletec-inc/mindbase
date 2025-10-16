"""
Integration tests for database operations.
"""
import pytest
from sqlalchemy import text


@pytest.mark.integration
@pytest.mark.asyncio
async def test_database_connection(db_session):
    """Test database connection is working."""
    result = await db_session.execute(text("SELECT 1"))
    assert result.scalar() == 1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_pgvector_extension(db_session):
    """Test pgvector extension is installed."""
    result = await db_session.execute(
        text("SELECT * FROM pg_extension WHERE extname = 'vector'")
    )
    extension = result.fetchone()
    assert extension is not None, "pgvector extension not installed"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_conversation_table_exists(db_session):
    """Test conversations table exists."""
    result = await db_session.execute(
        text(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'conversations')"
        )
    )
    exists = result.scalar()
    assert exists is True, "conversations table does not exist"
