"""
Pytest configuration and shared fixtures for MindBase tests.
"""
import asyncio
import os
from pathlib import Path
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config import Settings
from app.database import Base


# ========================================
# Test Configuration
# ========================================

@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """Test-specific settings."""
    return Settings(
        DATABASE_URL="postgresql+asyncpg://mindbase:mindbase_dev@localhost:15433/mindbase_test",
        OLLAMA_URL="http://localhost:11434",
        EMBEDDING_MODEL="qwen3-embedding:8b",
        DEBUG=True,
    )


# ========================================
# Database Fixtures
# ========================================

@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
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
    """Mock Ollama embedding response."""
    return {
        "embedding": [0.1] * 1024,  # 1024-dimensional vector
    }


@pytest.fixture
def sample_conversation_data() -> dict:
    """Sample conversation data for testing."""
    return {
        "source": "claude-code",
        "thread_id": "test-thread-123",
        "title": "Test Conversation",
        "project": "mindbase",
        "tags": ["test", "development"],
        "messages": [
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
        ],
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
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "e2e" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)
