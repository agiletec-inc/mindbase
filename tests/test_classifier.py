"""Unit tests for the topic/project classifier helpers."""

from app.services.classifier import infer_project, infer_topics


def test_infer_topics_with_keywords() -> None:
    text = "Docker containers and docker-compose scripts control the workspace deployment"
    topics = infer_topics(text)
    assert topics == ["Docker-First Development"]


def test_infer_topics_fallback() -> None:
    topics = infer_topics("Just a generic conversation")
    assert topics == ["General"]


def test_infer_project_prefers_explicit_metadata() -> None:
    text = "mindbase vector search"
    metadata = {"project": "mindbase"}
    project = infer_project(metadata=metadata, content=None, text=text, explicit=None)
    assert project == "mindbase"


def test_infer_project_heuristic() -> None:
    text = "SuperClaude PM agent notes"
    project = infer_project(metadata=None, content=None, text=text, explicit=None)
    assert project == "superclaude"
