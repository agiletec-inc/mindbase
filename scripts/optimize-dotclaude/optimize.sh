#!/bin/bash
# ~/.claude/ Optimization Script
# Keeps ~/.claude/ clean with latest data only, archives old conversations

set -euo pipefail

# Directories
CLAUDE_DIR="$HOME/.claude"
ARCHIVE_DIR="$HOME/Library/Application Support/mindbase/conversations/claude-code"
LOG_FILE="/tmp/dotclaude-optimizer.log"

# Logging
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

# Configuration
ARCHIVE_THRESHOLD_DAYS=${1:-90}
DRY_RUN=${DRY_RUN:-false}

log "🧹 Starting ~/.claude/ optimization"
log "📂 Directory: $CLAUDE_DIR"
log "⏰ Archive threshold: $ARCHIVE_THRESHOLD_DAYS days"
log "🔍 Dry run: $DRY_RUN"

# ===================================
# Step 1: Archive old conversations
# ===================================
log "📦 Step 1: Archiving old conversations"

old_conversations=$(find "$CLAUDE_DIR/projects" -name "*.jsonl" -type f -mtime +"$ARCHIVE_THRESHOLD_DAYS" 2>/dev/null | wc -l | xargs)
log "  Found $old_conversations conversations >$ARCHIVE_THRESHOLD_DAYS days old"

if [ "$DRY_RUN" = "false" ]; then
    bash ~/github/mindbase/scripts/collect-conversations/claude-code-collector.sh "$ARCHIVE_THRESHOLD_DAYS"
else
    log "  [DRY RUN] Would archive $old_conversations files"
fi

# ===================================
# Step 2: Clean temporary files
# ===================================
log "🗑️  Step 2: Cleaning temporary files"

# Find temp files
temp_files=$(find "$CLAUDE_DIR" -type f \( -name "*.tmp" -o -name "*.bak" -o -name "*.swp" -o -name "*~" \) 2>/dev/null)
temp_count=$(echo "$temp_files" | grep -c '\.' || echo "0")

log "  Found $temp_count temporary files"

if [ "$temp_count" -gt 0 ]; then
    if [ "$DRY_RUN" = "false" ]; then
        echo "$temp_files" | while read -r file; do
            if [ -f "$file" ]; then
                rm "$file"
                log "  ✅ Deleted: $(basename "$file")"
            fi
        done
    else
        echo "$temp_files" | while read -r file; do
            log "  [DRY RUN] Would delete: $(basename "$file")"
        done
    fi
fi

# ===================================
# Step 3: Preserve essential files
# ===================================
log "✅ Step 3: Verifying essential files"

essential_files=(
    "CLAUDE.md"
    "COMMANDS.md"
    "FLAGS.md"
    "MCP.md"
    "PERSONAS.md"
    "settings.local.json"
)

for file in "${essential_files[@]}"; do
    if [ -f "$CLAUDE_DIR/$file" ]; then
        log "  ✓ $file (preserved)"
    else
        log "  ⚠️  $file (missing)"
    fi
done

# Check MODE_*.md files
mode_count=$(find "$CLAUDE_DIR" -maxdepth 1 -name "MODE_*.md" -type f 2>/dev/null | wc -l | xargs)
log "  ✓ MODE_*.md: $mode_count files (preserved)"

# ===================================
# Step 4: Summary statistics
# ===================================
log "📊 Step 4: Summary statistics"

total_jsonl=$(find "$CLAUDE_DIR/projects" -name "*.jsonl" -type f 2>/dev/null | wc -l | xargs)
total_size=$(du -sh "$CLAUDE_DIR" 2>/dev/null | awk '{print $1}')
archived_total=$(find "$ARCHIVE_DIR" -name "*.jsonl" -type f 2>/dev/null | wc -l | xargs)

log "  Current .claude size: $total_size"
log "  Active conversations: $total_jsonl files"
log "  Total archived: $archived_total files"

# ===================================
# Step 5: Recommendations
# ===================================
log "💡 Step 5: Recommendations"

if [ "$total_jsonl" -gt 50 ]; then
    log "  ⚠️  High conversation count ($total_jsonl). Consider running:"
    log "     DRY_RUN=false $0 60  # Archive conversations >60 days"
fi

log "✅ Optimization complete"
log "📝 Log saved to: $LOG_FILE"
