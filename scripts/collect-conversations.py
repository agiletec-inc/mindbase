#!/usr/bin/env python3
"""
MindBase Conversation Collector

Collects conversations from local LLM clients (Claude Desktop, ChatGPT Desktop,
Cursor, WindSurf, Claude Code) and stores them via the MindBase REST API.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional

import requests

# Ensure project root is on sys.path when running from scripts/
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from collectors import (  # noqa: E402
    ChatGPTCollector,
    ClaudeDesktopCollector,
    Conversation,
    CursorCollector,
    DataNormalizer,
    Message,
    WindsurfCollector,
)

LOGGER = logging.getLogger("mindbase.collector")

DEFAULT_API_URL = os.getenv("MINDBASE_API_URL", "http://localhost:18002")
DEFAULT_BATCH_SIZE = 20
DEFAULT_WORKSPACE = os.getenv("WORKSPACE_ROOT")

CollectorRegistry = Dict[str, type[ClaudeDesktopCollector]]

COLLECTOR_REGISTRY: CollectorRegistry = {
    "claude-desktop": ClaudeDesktopCollector,
    "chatgpt": ChatGPTCollector,
    "cursor": CursorCollector,
    "windsurf": WindsurfCollector,
    # claude-code is backed by JSONL and currently covered by module processors
}


class MindBaseAPISyncer:
    """Sync conversations to the MindBase FastAPI backend."""

    def __init__(self, base_url: str, api_key: Optional[str] = None, timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        if api_key:
            self.session.headers["Authorization"] = f"Bearer {api_key}"
        self.timeout = timeout

    def store_conversation(self, payload: Dict) -> Dict:
        """POST a conversation payload to /conversations/store."""
        url = f"{self.base_url}/conversations/store"
        response = self.session.post(url, json=payload, timeout=self.timeout)
        if response.status_code >= 400:
            raise RuntimeError(
                f"Failed to store conversation (status {response.status_code}): {response.text}"
            )
        return response.json()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect and sync AI conversations to MindBase"
    )
    parser.add_argument(
        "--source",
        choices=list(COLLECTOR_REGISTRY.keys()) + ["all"],
        default="all",
        help="Conversation source to collect",
    )
    parser.add_argument(
        "--since",
        type=str,
        help="Collect conversations updated since ISO timestamp (e.g. 2025-01-16T00:00:00Z)",
    )
    parser.add_argument(
        "--api-url",
        type=str,
        default=DEFAULT_API_URL,
        help=f"MindBase API base URL (default: {DEFAULT_API_URL})",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=os.getenv("MINDBASE_API_KEY"),
        help="Optional API key for authenticated deployments",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help="Number of conversations to sync per batch",
    )
    parser.add_argument(
        "--workspace",
        type=str,
        default=DEFAULT_WORKSPACE,
        help="Workspace root path (defaults to WORKSPACE_ROOT env or current directory)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Collect and display stats without syncing to API",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable debug logging",
    )
    return parser.parse_args()


def parse_since(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if not dt.tzinfo:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError as exc:
        raise ValueError(f"Invalid --since value: {value}") from exc


def get_collectors(selected: str) -> List[ClaudeDesktopCollector]:
    if selected == "all":
        sources = list(COLLECTOR_REGISTRY.keys())
    else:
        sources = [selected]

    collectors: List[ClaudeDesktopCollector] = []
    for source in sources:
        collector_cls = COLLECTOR_REGISTRY.get(source)
        if not collector_cls:
            raise KeyError(f"Unsupported source: {source}")
        collectors.append(collector_cls())
    return collectors


def message_to_dict(message: Message) -> Dict:
    return {
        "role": message.role,
        "content": message.content,
        "timestamp": message.timestamp.isoformat() if message.timestamp else None,
        "metadata": message.metadata or {},
    }


def conversation_to_payload(conversation: Conversation) -> Dict:
    messages = [message_to_dict(msg) for msg in conversation.messages]
    content: Dict[str, object] = {"messages": messages}
    if conversation.thread_id:
        content["thread_id"] = conversation.thread_id
    if conversation.project:
        content["project"] = conversation.project
    if conversation.tags:
        content["tags"] = conversation.tags
    if conversation.workspace:
        content["workspace"] = conversation.workspace

    payload: Dict[str, object] = {
        "source": conversation.source,
        "source_conversation_id": conversation.thread_id or conversation.id,
        "title": conversation.title,
        "content": content,
        "metadata": conversation.metadata or {},
    }

    if conversation.created_at:
        payload["source_created_at"] = conversation.created_at.isoformat()
    if conversation.project:
        payload["project"] = conversation.project
    if conversation.tags:
        payload["topics"] = conversation.tags
    if conversation.workspace:
        payload["workspace"] = conversation.workspace
        if payload["metadata"] is None:
            payload["metadata"] = {}
        payload["metadata"]["workspace"] = conversation.workspace

    return payload


def chunk_iterable(items: Iterable, chunk_size: int) -> Iterable[List]:
    batch: List = []
    for item in items:
        batch.append(item)
        if len(batch) >= chunk_size:
            yield batch
            batch = []
    if batch:
        yield batch


def main() -> int:
    args = parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    since_dt = parse_since(args.since)
    collectors = get_collectors(args.source)
    workspace_path = args.workspace or os.getenv("WORKSPACE_ROOT")
    if not workspace_path:
        workspace_path = os.getcwd()
    workspace_path = os.path.abspath(workspace_path)
    normalizer = DataNormalizer()

    total_collected = 0
    normalized_conversations: List[Conversation] = []

    for collector in collectors:
        LOGGER.info("Collecting from %s ...", collector.source_name)
        raw_conversations = collector.collect(since_dt)
        total_collected += len(raw_conversations)

        normalized = normalizer.normalize_conversations(raw_conversations, collector.source_name)
        for conv in normalized:
            if not conv.workspace:
                conv.workspace = workspace_path
            normalized_conversations.append(conv)

        stats = collector.get_stats()
        LOGGER.info(
            "Source %s: %s conversations, %s messages",
            collector.source_name,
            stats["total_conversations"],
            stats["total_messages"],
        )

    LOGGER.info(
        "Collected %s raw conversations, %s after normalization",
        total_collected,
        len(normalized_conversations),
    )

    if args.dry_run:
        LOGGER.info("Dry run enabled: skipping API sync")
        for conv in normalized_conversations[:5]:
            preview = json.dumps(conversation_to_payload(conv), ensure_ascii=False, indent=2)
            LOGGER.debug("Sample payload:\n%s", preview)
        return 0

    syncer = MindBaseAPISyncer(args.api_url, args.api_key)
    successes = 0
    failures: List[Dict[str, str]] = []

    for batch in chunk_iterable(normalized_conversations, args.batch_size):
        for conv in batch:
            payload = conversation_to_payload(conv)
            try:
                response = syncer.store_conversation(payload)
                LOGGER.debug(
                    "Stored conversation %s (id=%s)",
                    conv.id,
                    response.get("id"),
                )
                successes += 1
            except Exception as exc:
                LOGGER.error("Failed to store conversation %s: %s", conv.id, exc)
                failures.append({"conversation_id": conv.id, "error": str(exc)})

    LOGGER.info("Sync complete: %s success, %s failures", successes, len(failures))

    if failures:
        failure_log = os.path.join("/tmp", "mindbase-sync-failures.json")
        with open(failure_log, "w") as fh:
            json.dump(failures, fh, indent=2)
        LOGGER.warning("Failure details written to %s", failure_log)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
