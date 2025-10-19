#!/usr/bin/env python3
"""
Import Claude Code conversation history from ~/.claude/history.jsonl
"""

import json
import subprocess
from pathlib import Path
from datetime import datetime
import sys

# MindBase API endpoint
API_URL = "http://localhost:18002"

def import_claude_code_history():
    """Import Claude Code conversation history"""

    history_file = Path.home() / ".claude" / "history.jsonl"

    if not history_file.exists():
        print(f"❌ History file not found: {history_file}")
        return

    print(f"📂 Reading history from: {history_file}")

    # Parse JSONL
    conversations = []
    with open(history_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            try:
                data = json.loads(line.strip())

                # Extract basic info
                display = data.get('display', '')
                timestamp_ms = data.get('timestamp', 0)
                project = data.get('project', 'unknown')

                if not display:
                    continue

                # Convert timestamp
                created_at = datetime.fromtimestamp(timestamp_ms / 1000) if timestamp_ms else datetime.now()

                # Extract project name from path
                project_name = Path(project).name if project != 'unknown' else 'general'

                # Detect emotional tags (simple heuristics)
                emotional_tags = []
                if any(word in display.lower() for word in ['なんで', 'おかしくない', 'だろって', '理解してんのか']):
                    emotional_tags.append('frustrated')
                if any(word in display.lower() for word in ['ちゃんと', '必ず', 'しろよ']):
                    emotional_tags.append('corrected')
                if '？？' in display or '！！' in display:
                    emotional_tags.append('emphasis')

                # Prepare conversation item
                conversation = {
                    "source": "claude-code",
                    "title": display[:100],  # First 100 chars as title
                    "content": {
                        "messages": [
                            {
                                "role": "user",
                                "content": display,
                                "timestamp": created_at.isoformat()
                            }
                        ]
                    },
                    "metadata": {
                        "project": project_name,
                        "project_path": project,
                        "emotional_tags": emotional_tags,
                        "line_number": line_num
                    },
                    "category": "note" if not emotional_tags else ("warning" if "corrected" in emotional_tags else "note"),
                    "priority": "high" if "frustrated" in emotional_tags else "normal"
                }

                conversations.append(conversation)

            except Exception as e:
                print(f"⚠️  Error parsing line {line_num}: {e}")
                continue

    print(f"✅ Parsed {len(conversations)} conversations")

    # Import to MindBase via API (using curl)
    success_count = 0
    error_count = 0

    for idx, conv in enumerate(conversations, 1):
        try:
            # Use curl to POST JSON
            result = subprocess.run(
                [
                    'curl', '-s', '-X', 'POST',
                    f"{API_URL}/conversations/store",
                    '-H', 'Content-Type: application/json',
                    '-d', json.dumps(conv)
                ],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0 and '"id"' in result.stdout:
                success_count += 1
                if idx % 10 == 0:
                    print(f"📊 Progress: {idx}/{len(conversations)} ({success_count} success, {error_count} errors)")
            else:
                error_count += 1
                print(f"❌ Failed to store conversation {idx}: {result.stdout[:100]}")

        except Exception as e:
            error_count += 1
            print(f"❌ Error storing conversation {idx}: {e}")

    print(f"\n✅ Import complete!")
    print(f"   Success: {success_count}")
    print(f"   Errors: {error_count}")
    print(f"   Total: {len(conversations)}")

if __name__ == "__main__":
    import_claude_code_history()
