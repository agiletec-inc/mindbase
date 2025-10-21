"""
Unit tests for Memory System (Serena-inspired).
"""
import pytest
from pathlib import Path
import tempfile
import os


@pytest.mark.unit
class TestMemorySystem:
    """Test Memory System functionality."""

    def test_memory_write_creates_markdown_file(self, tmp_path):
        """Test memory_write creates markdown file."""
        from apps.mcp_server.storage.memory_fs import FileSystemMemoryBackend

        backend = FileSystemMemoryBackend(baseDir=str(tmp_path))

        # Write memory
        path = backend.writeMemory(
            name="test_memory",
            content="# Test Memory\n\nThis is a test.",
            metadata={
                "category": "note",
                "project": "mindbase",
                "tags": ["test"]
            }
        )

        # Verify file exists
        assert Path(path).exists()
        assert Path(path).name == "test_memory.md"

        # Verify content
        content = Path(path).read_text()
        assert "# Test Memory" in content
        assert "category: note" in content

    def test_memory_read_returns_memory(self, tmp_path):
        """Test memory_read retrieves memory."""
        from apps.mcp_server.storage.memory_fs import FileSystemMemoryBackend

        backend = FileSystemMemoryBackend(baseDir=str(tmp_path))

        # Write memory
        backend.writeMemory(
            name="test_memory",
            content="# Test Content",
            metadata={"category": "decision"}
        )

        # Read memory
        memory = backend.readMemory("test_memory")

        assert memory is not None
        assert memory["name"] == "test_memory"
        assert memory["category"] == "decision"
        assert "# Test Content" in memory["content"]

    def test_memory_list_filters_by_project(self, tmp_path):
        """Test memory_list filters by project."""
        from apps.mcp_server.storage.memory_fs import FileSystemMemoryBackend

        backend = FileSystemMemoryBackend(baseDir=str(tmp_path))

        # Write memories
        backend.writeMemory("memory1", "Content 1", {"project": "projectA"})
        backend.writeMemory("memory2", "Content 2", {"project": "projectB"})
        backend.writeMemory("memory3", "Content 3", {"project": "projectA"})

        # List projectA memories
        memories = backend.listMemories(filters={"project": "projectA"})

        assert len(memories) == 2
        names = [m["name"] for m in memories]
        assert "memory1" in names
        assert "memory3" in names
        assert "memory2" not in names

    def test_memory_delete_removes_file(self, tmp_path):
        """Test memory_delete removes markdown file."""
        from apps.mcp_server.storage.memory_fs import FileSystemMemoryBackend

        backend = FileSystemMemoryBackend(baseDir=str(tmp_path))

        # Write memory
        path = backend.writeMemory("test_memory", "Content")

        # Verify exists
        assert Path(path).exists()

        # Delete memory
        backend.deleteMemory("test_memory")

        # Verify deleted
        assert not Path(path).exists()

    def test_memory_validates_category(self, tmp_path):
        """Test memory validates category enum."""
        from apps.mcp_server.storage.memory_fs import FileSystemMemoryBackend

        backend = FileSystemMemoryBackend(baseDir=str(tmp_path))

        # Invalid category should raise error
        with pytest.raises(ValueError):
            backend.writeMemory(
                "test",
                "Content",
                {"category": "invalid_category"}
            )

        # Valid categories should work
        valid_categories = ["architecture", "decision", "pattern", "guide", "onboarding", "note"]
        for category in valid_categories:
            backend.writeMemory(
                f"test_{category}",
                "Content",
                {"category": category}
            )


@pytest.mark.unit
class TestMemoryEnvironmentVariables:
    """Test Memory System respects environment variables."""

    def test_memory_uses_env_base_dir(self, monkeypatch):
        """Test MEMORY_BASE_DIR environment variable."""
        from apps.mcp_server.storage.memory_fs import FileSystemMemoryBackend

        test_dir = "/tmp/test_memories"
        monkeypatch.setenv("MEMORY_BASE_DIR", test_dir)

        backend = FileSystemMemoryBackend()

        assert backend.baseDir == test_dir

    def test_memory_fails_without_ollama_url_for_search(self):
        """Test memory_search requires OLLAMA_URL."""
        from apps.mcp_server.storage.memory_fs import FileSystemMemoryBackend

        backend = FileSystemMemoryBackend()

        # Should fail without OLLAMA_URL
        with pytest.raises(ValueError, match="OLLAMA_URL"):
            backend.searchMemories("test query")
