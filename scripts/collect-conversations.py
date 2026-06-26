#!/usr/bin/env python3
"""Collect conversations from a local source and POST them to the MindBase API.

This is the Python counterpart to `apps/cli/commands/collect.ts` (which only
handles claude-code). collect.ts points other sources here. It runs on the HOST
(not in a container) because the collectors read host paths like
~/Library/Application Support/... and ~/.claude.

Usage:
    python scripts/collect-conversations.py --source chatgpt --dry-run
    python scripts/collect-conversations.py --source cursor --since 2024-01-01
    python scripts/collect-conversations.py --source chatgpt \
        --export-file ~/Downloads/chatgpt-export/conversations.json

Sources: chatgpt | claude-desktop | claude-code | cursor | windsurf | gemini

The API URL defaults to the host-published port from .env (18002). Override with
--api-url or MINDBASE_API_URL.
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

# Make `libs.collectors.*` importable when run from the repo root on the host.
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from libs.collectors.base_collector import Conversation  # noqa: E402

# source name -> (module, class)
COLLECTORS = {
    "chatgpt": ("libs.collectors.chatgpt_collector", "ChatGPTCollector"),
    "claude-desktop": ("libs.collectors.claude_collector", "ClaudeDesktopCollector"),
    "claude-code": ("libs.collectors.claude_code_collector", "ClaudeCodeCollector"),
    "cursor": ("libs.collectors.cursor_collector", "CursorCollector"),
    "windsurf": ("libs.collectors.windsurf_collector", "WindsurfCollector"),
    "gemini": ("libs.collectors.gemini_collector", "GeminiCollector"),
}


def load_collector(source: str):
    import importlib

    if source not in COLLECTORS:
        raise SystemExit(
            f"Unknown source '{source}'. Choices: {', '.join(COLLECTORS)}"
        )
    mod_name, cls_name = COLLECTORS[source]
    mod = importlib.import_module(mod_name)
    return getattr(mod, cls_name)()


def to_payload(conv: Conversation) -> dict:
    """Map a collector Conversation dataclass to the API ConversationCreate body."""
    messages = []
    for m in conv.messages:
        ts = getattr(m, "timestamp", None)
        messages.append(
            {
                "role": m.role,
                "content": m.content,
                "timestamp": ts.isoformat() if isinstance(ts, datetime) else None,
            }
        )
    metadata = dict(conv.metadata or {})
    if conv.project:
        metadata.setdefault("project", conv.project)
    if conv.workspace:
        metadata.setdefault("workspace", conv.workspace)
    if conv.tags:
        metadata.setdefault("tags", conv.tags)
    return {
        "source": conv.source,
        "source_conversation_id": conv.thread_id or conv.id,
        "title": conv.title,
        "content": {"messages": messages},
        "metadata": metadata,
        "source_created_at": conv.created_at.isoformat() if conv.created_at else None,
    }


def post_conversation(api_url: str, payload: dict, timeout: float = 60.0) -> tuple[bool, str]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{api_url.rstrip('/')}/conversations/store",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return True, f"{resp.status}"
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:300]}"
    except Exception as e:  # noqa: BLE001 — surface the failure, never swallow it
        return False, f"{type(e).__name__}: {e}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", required=True, choices=list(COLLECTORS))
    ap.add_argument("--since", help="ISO date, e.g. 2024-01-01 — only newer conversations")
    ap.add_argument("--limit", type=int, default=0, help="Max conversations to send (0 = all)")
    ap.add_argument("--dry-run", action="store_true", help="Collect and report, do not POST")
    ap.add_argument(
        "--export-file",
        help="Path to an official export JSON (ChatGPT/Claude). Overrides default scan paths.",
    )
    ap.add_argument(
        "--api-url",
        default=os.environ.get("MINDBASE_API_URL", "http://localhost:18002"),
    )
    args = ap.parse_args()

    since = None
    if args.since:
        since = datetime.fromisoformat(args.since).replace(tzinfo=timezone.utc)

    collector = load_collector(args.source)

    # Official exports: feed the file directly through the collector's JSON path.
    if args.export_file:
        export_path = Path(args.export_file).expanduser()
        if not export_path.exists():
            raise SystemExit(f"--export-file not found: {export_path}")
        if not hasattr(collector, "_collect_from_json"):
            raise SystemExit(
                f"{args.source} collector has no JSON-export path (_collect_from_json)."
            )
        conversations = collector._collect_from_json(export_path, since)
    else:
        conversations = collector.collect(since)

    print(f"[{args.source}] collected {len(conversations)} conversations")
    if args.limit:
        conversations = conversations[: args.limit]
        print(f"[{args.source}] limited to {len(conversations)}")

    if args.dry_run:
        for c in conversations[:5]:
            n = len(c.messages)
            when = c.created_at.date().isoformat() if c.created_at else "?"
            print(f"  - [{when}] {(c.title or '(untitled)')[:70]}  ({n} msgs)")
        if len(conversations) > 5:
            print(f"  ... and {len(conversations) - 5} more")
        return 0

    ok = 0
    fail = 0
    for i, conv in enumerate(conversations, 1):
        success, info = post_conversation(args.api_url, to_payload(conv))
        if success:
            ok += 1
        else:
            fail += 1
            print(f"  ! [{i}/{len(conversations)}] {conv.title!r}: {info}")
        if i % 25 == 0:
            print(f"  ... {i}/{len(conversations)} (ok={ok} fail={fail})")
    print(f"[{args.source}] done: stored={ok} failed={fail}")
    return 1 if fail and ok == 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
