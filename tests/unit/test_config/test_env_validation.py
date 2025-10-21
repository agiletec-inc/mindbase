"""
Unit tests for environment variable validation.

Tests that apps fail-fast with clear errors when required env vars are missing.
"""
import pytest
import os
import subprocess
import sys


@pytest.mark.unit
class TestPythonAPIEnvValidation:
    """Test Python API (FastAPI) environment variable validation."""

    def test_api_requires_database_url(self, monkeypatch):
        """Test API fails without DATABASE_URL."""
        from pydantic import ValidationError
        from apps.api.config import Settings

        # Remove DATABASE_URL
        monkeypatch.delenv("DATABASE_URL", raising=False)

        # Should raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            Settings()

        assert "DATABASE_URL" in str(exc_info.value)

    def test_api_requires_ollama_url(self, monkeypatch):
        """Test API fails without OLLAMA_URL."""
        from pydantic import ValidationError
        from apps.api.config import Settings

        # Set DATABASE_URL but remove OLLAMA_URL
        monkeypatch.setenv("DATABASE_URL", "postgresql://test")
        monkeypatch.delenv("OLLAMA_URL", raising=False)

        # Should raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            Settings()

        assert "OLLAMA_URL" in str(exc_info.value)

    def test_api_requires_embedding_model(self, monkeypatch):
        """Test API fails without EMBEDDING_MODEL."""
        from pydantic import ValidationError
        from apps.api.config import Settings

        # Set required vars but remove EMBEDDING_MODEL
        monkeypatch.setenv("DATABASE_URL", "postgresql://test")
        monkeypatch.setenv("OLLAMA_URL", "http://localhost:11434")
        monkeypatch.delenv("EMBEDDING_MODEL", raising=False)

        # Should raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            Settings()

        assert "EMBEDDING_MODEL" in str(exc_info.value)


@pytest.mark.unit
class TestDockerComposeEnvValidation:
    """Test docker-compose.yml requires environment variables."""

    def test_docker_compose_no_hardcoded_ports(self, tmp_path):
        """Test docker-compose.yml has no hardcoded port numbers."""
        compose_file = tmp_path.parent.parent / "docker-compose.yml"

        if not compose_file.exists():
            pytest.skip("docker-compose.yml not found")

        content = compose_file.read_text()

        # Check for common hardcoded patterns
        forbidden_patterns = [
            "5432:5432",
            "11434:11434",
            "18002:8000",
            "18003:8000",
            "15434:5432",
        ]

        for pattern in forbidden_patterns:
            assert pattern not in content, f"Found hardcoded port mapping: {pattern}"

    def test_docker_compose_uses_env_vars(self, tmp_path):
        """Test docker-compose.yml uses ${VAR} syntax."""
        compose_file = tmp_path.parent.parent / "docker-compose.yml"

        if not compose_file.exists():
            pytest.skip("docker-compose.yml not found")

        content = compose_file.read_text()

        # Should use environment variable syntax
        required_env_vars = [
            "${POSTGRES_PORT}",
            "${API_PORT}",
            "${DATABASE_URL}",
            "${OLLAMA_URL}",
        ]

        for var in required_env_vars:
            assert var in content, f"docker-compose.yml should reference {var}"


@pytest.mark.unit
class TestEnvExampleCompleteness:
    """.env.example should have all required variables."""

    def test_env_example_has_warning(self, tmp_path):
        """Test .env.example has hardcoding warning."""
        env_example = tmp_path.parent.parent / ".env.example"

        if not env_example.exists():
            pytest.skip(".env.example not found")

        content = env_example.read_text()

        assert "NEVER HARDCODE" in content or "⚠️" in content

    def test_env_example_has_all_required_vars(self, tmp_path):
        """Test .env.example defines all required variables."""
        env_example = tmp_path.parent.parent / ".env.example"

        if not env_example.exists():
            pytest.skip(".env.example not found")

        content = env_example.read_text()

        # Required variables
        required_vars = [
            "POSTGRES_HOST",
            "POSTGRES_PORT",
            "POSTGRES_USER",
            "POSTGRES_PASSWORD",
            "POSTGRES_DB",
            "OLLAMA_HOST",
            "OLLAMA_PORT",
            "EMBEDDING_MODEL",
            "EMBEDDING_DIMENSIONS",
            "API_HOST",
            "API_PORT",
            "DATABASE_URL",
            "OLLAMA_URL",
        ]

        for var in required_vars:
            assert var in content, f".env.example missing {var}"
