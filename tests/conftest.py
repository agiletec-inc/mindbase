"""
Pytest configuration and shared fixtures for MindBase tests.
"""
import asyncio
import os
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from collectors.base_collector import Message
from app.config import Settings
from app.database import Base


# ========================================
# Test Configuration
# ========================================

@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """Test-specific settings.

    ⚠️ Uses environment variables for all configuration.
    Set TEST_DATABASE_URL, TEST_OLLAMA_URL in environment or CI.
    """
    return Settings(
        DATABASE_URL=os.getenv(
            "TEST_DATABASE_URL",
            os.getenv("DATABASE_URL", "")
        ),
        OLLAMA_URL=os.getenv(
            "TEST_OLLAMA_URL",
            os.getenv("OLLAMA_URL", "")
        ),
        EMBEDDING_MODEL=os.getenv("EMBEDDING_MODEL", "qwen3-embedding:8b"),
        EMBEDDING_DIMENSIONS=int(os.getenv("EMBEDDING_DIMENSIONS", "1024")),
        DEBUG=True,
    )


# ========================================
# Database Fixtures
# ========================================

@pytest_asyncio.fixture
async def test_engine(test_settings: Settings) -> AsyncGenerator[AsyncEngine, None]:
    """Create test database engine."""
    engine = create_async_engine(
        test_settings.DATABASE_URL,
        echo=test_settings.DEBUG,
        future=True,
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Create database session for tests."""
    async_session = sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        yield session
        await session.rollback()


# ========================================
# File System Fixtures
# ========================================

@pytest.fixture
def test_data_dir() -> Path:
    """Get test data directory."""
    return Path(__file__).parent / "data"


@pytest.fixture
def sample_conversation_file(test_data_dir: Path) -> Path:
    """Get sample conversation JSON file."""
    return test_data_dir / "sample_conversation.json"


@pytest.fixture
def temp_archive_dir(tmp_path: Path) -> Path:
    """Create temporary archive directory."""
    archive_dir = tmp_path / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    return archive_dir


# ========================================
# Mock Fixtures
# ========================================

@pytest.fixture
def mock_ollama_response() -> dict:
    """Mock Ollama embedding response (qwen3-embedding:8b: 1024-dim)."""
    return {
        "embedding": [0.1] * 1024,  # 1024-dimensional vector (qwen3-embedding:8b)
    }


@pytest.fixture
def sample_conversation_messages() -> list[dict[str, str]]:
    """Sample message payload used by multiple fixtures."""
    return [
        {
            "role": "user",
            "content": "Hello, this is a test message",
            "timestamp": "2025-01-16T10:00:00Z",
        },
        {
            "role": "assistant",
            "content": "This is a test response",
            "timestamp": "2025-01-16T10:00:01Z",
        },
    ]


@pytest.fixture
def sample_conversation_data(sample_conversation_messages) -> dict:
    """Dataclass-friendly conversation for collector tests."""

    def to_datetime(value: str) -> datetime:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)

    messages = [
        Message(
            role=msg["role"],
            content=msg["content"],
            timestamp=to_datetime(msg["timestamp"]),
        )
        for msg in sample_conversation_messages
    ]

    created = messages[0].timestamp
    updated = messages[-1].timestamp

    return {
        "id": "conv-test-123",
        "source": "claude-code",
        "title": "Test Conversation",
        "messages": messages,
        "created_at": created,
        "updated_at": updated,
        "thread_id": "test-thread-123",
        "project": "mindbase",
        "tags": ["test", "development"],
        "metadata": {"model": "claude-sonnet-4.5", "temperature": 0.7},
    }


@pytest.fixture
def api_conversation_payload(sample_conversation_messages) -> dict:
    """API payload matching ConversationCreate schema."""
    messages = deepcopy(sample_conversation_messages)
    return {
        "source": "claude-code",
        "source_conversation_id": "test-thread-123",
        "title": "Test Conversation",
        "content": {
            "messages": messages,
            "tags": ["test", "development"],
            "project": "mindbase",
        },
        "metadata": {
            "model": "claude-sonnet-4.5",
            "temperature": 0.7,
        },
    }


# ========================================
# Pytest Hooks
# ========================================

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as unit test (fast, isolated)"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test (requires services)"
    )
    config.addinivalue_line(
        "markers", "e2e: mark test as end-to-end test (full pipeline)"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow (>1s execution)"
    )


def pytest_collection_modifyitems(config, items):
    """Automatically mark tests based on location."""
    for item in items:
        # Mark tests by directory
        path = str(item.fspath)
        if "unit" in path:
            item.add_marker(pytest.mark.unit)
        elif "integration" in path:
            item.add_marker(pytest.mark.integration)
            item.add_marker(pytest.mark.asyncio(loop_scope="session"))
        elif "e2e" in path:
            item.add_marker(pytest.mark.e2e)
            item.add_marker(pytest.mark.asyncio(loop_scope="session"))
