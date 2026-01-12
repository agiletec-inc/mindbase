"""
Pytest configuration and shared fixtures for MindBase tests.
"""
import os
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool
from libs.collectors.base_collector import Message
from app.config import Settings
from app.database import Base
from app.models.conversation import Conversation, RawConversation  # noqa: F401


@pytest_asyncio.fixture
async def async_client(
    test_engine: AsyncEngine,
) -> AsyncGenerator["AsyncClient", None]:
    """Async HTTP client bound to the FastAPI app."""
    from httpx import AsyncClient
    from app.main import app
    from app.database import get_db

    async_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async def override_get_db():
        async with async_session() as session:
            try:
                yield session
            finally:
                await session.rollback()

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

    app.dependency_overrides.pop(get_db, None)


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
            os.getenv("DATABASE_URL", "postgresql+asyncpg://mindbase:mindbase_dev@postgres:5432/mindbase_test")
        ),
        OLLAMA_URL=os.getenv(
            "TEST_OLLAMA_URL",
            os.getenv("OLLAMA_URL", "")
        ),
        EMBEDDING_MODEL=os.getenv("EMBEDDING_MODEL", "qwen3-embedding:8b"),
        EMBEDDING_DIMENSIONS=int(os.getenv("EMBEDDING_DIMENSIONS", "4096")),
        DEBUG=True,
    )


# ========================================
# Database Fixtures
# ========================================

@pytest_asyncio.fixture(scope="session")
async def ensure_test_database(test_settings: Settings) -> None:
    """Ensure the dedicated test database and required extensions exist."""
    url = make_url(test_settings.DATABASE_URL)

    admin_url = url.set(database="postgres")
    admin_engine = create_async_engine(
        admin_url,
        isolation_level="AUTOCOMMIT",
        future=True,
        poolclass=NullPool,
    )

    async with admin_engine.begin() as conn:
        result = await conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"),
            {"name": url.database},
        )
        if result.scalar() is None:
            await conn.execute(text(f'CREATE DATABASE "{url.database}"'))
    await admin_engine.dispose()

    # Ensure extensions inside the test database
    extension_engine = create_async_engine(
        test_settings.DATABASE_URL,
        isolation_level="AUTOCOMMIT",
        future=True,
        poolclass=NullPool,
    )
    async with extension_engine.begin() as conn:
        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";'))
        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "vector";'))
        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "pg_trgm";'))
    await extension_engine.dispose()


@pytest_asyncio.fixture
async def test_engine(
    ensure_test_database: None,
    test_settings: Settings,
) -> AsyncGenerator[AsyncEngine, None]:
    """Create test database engine."""
    if "test" not in test_settings.DATABASE_URL:
        raise RuntimeError(
            f"Refusing to run tests against non-test database: {test_settings.DATABASE_URL}"
        )
    engine = create_async_engine(
        test_settings.DATABASE_URL,
        echo=test_settings.DEBUG,
        future=True,
        poolclass=NullPool,
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
    async_session = async_sessionmaker(
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
    """Mock Ollama embedding response (qwen3-embedding:8b: 4096-dim)."""
    return {
        "embedding": [0.1] * 4096,
    }


@pytest.fixture(autouse=True)
def stub_ollama_requests(monkeypatch, test_settings: Settings):
    """Stub Ollama HTTP calls to avoid hitting external services."""
    from httpx import Response, Request
    from app.ollama_client import OllamaClient, ollama_client

    async def fake_request(self, method: str, path: str, **kwargs):
        request = Request(method, f"{self.base_url}{path}")
        if path == "/api/version":
            return Response(200, json={"version": "mock"}, request=request)
        if path == "/api/tags":
            return Response(
                200,
                json={"models": [{"name": self.model}]},
                request=request,
            )
        if path == "/api/embeddings":
            return Response(
                200,
                json={"embedding": [0.1] * test_settings.EMBEDDING_DIMENSIONS},
                request=request,
            )
        return Response(200, json={}, request=request)

    monkeypatch.setattr(OllamaClient, "_request", fake_request, raising=False)

    # Ensure shared client uses the same behaviour
    async def fake_embed(text: str):
        return [0.1] * test_settings.EMBEDDING_DIMENSIONS

    async def fake_embed_batch(texts):
        return [[0.1] * test_settings.EMBEDDING_DIMENSIONS for _ in texts]

    monkeypatch.setattr(ollama_client, "embed", fake_embed, raising=False)
    monkeypatch.setattr(ollama_client, "embed_batch", fake_embed_batch, raising=False)


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
        "workspace": "/workspaces/tests",
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
            item.add_marker(pytest.mark.asyncio(loop_scope="function"))
        elif "e2e" in path:
            item.add_marker(pytest.mark.e2e)
            item.add_marker(pytest.mark.asyncio(loop_scope="function"))
