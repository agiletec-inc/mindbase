#!/bin/bash
# Research script to find conversation data from all AI apps

echo "🔍 AI Conversation Data Location Research"
echo "=========================================="
echo ""

# Claude Code
echo "📦 Claude Code (.jsonl files):"
find ~/.claude -name "*.jsonl" -type f 2>/dev/null | head -10
echo "  Total: $(find ~/.claude -name "*.jsonl" -type f 2>/dev/null | wc -l) files"
echo ""

# Claude Desktop
echo "📦 Claude Desktop:"
find ~/Library/Application\ Support/Claude -type f 2>/dev/null | head -10
echo "  Check for: conversations.db, conversations.json"
ls -lah ~/Library/Application\ Support/Claude/ 2>/dev/null | grep -E "conversation|chat|message"
echo ""

# ChatGPT
echo "📦 ChatGPT Desktop:"
find ~/Library/Application\ Support -name "*chatgpt*" -o -name "*openai*" -type d 2>/dev/null
find ~/Library/Application\ Support/com.openai.chat -type f 2>/dev/null | head -10
echo ""

# Cursor
echo "📦 Cursor:"
find ~/Library/Application\ Support/Cursor -type f 2>/dev/null | head -10
ls -lah ~/Library/Application\ Support/Cursor/ 2>/dev/null | grep -E "conversation|chat|message|history"
echo ""

# Windsurf
echo "📦 Windsurf:"
find ~/Library/Application\ Support/Windsurf -type f 2>/dev/null | head -10
find ~/Library/Application\ Support -name "*windsurf*" -type d 2>/dev/null
echo ""

# Zed
echo "📦 Zed:"
find ~/Library/Application\ Support/Zed -type f 2>/dev/null | head -10
find ~/Library/Application\ Support -name "*zed*" -type d 2>/dev/null
echo ""

# VS Code
echo "📦 VS Code (Copilot):"
find ~/Library/Application\ Support/Code -type f 2>/dev/null | grep -i "copilot\|chat" | head -10
echo ""

# Summary
echo "=========================================="
echo "📊 Summary:"
echo ""
echo "Claude Code: $(find ~/.claude -name "*.jsonl" -type f 2>/dev/null | wc -l) conversation files"
echo ""
echo "🎯 Next Steps:"
echo "1. Inspect actual file formats"
echo "2. Implement specific parsers for each app"
echo "3. Test data extraction"
