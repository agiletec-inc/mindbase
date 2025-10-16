#!/bin/bash
# Claude Code Conversation Collector
# Collects .jsonl conversations from ~/.claude/projects/ and archives to Application Support

set -euo pipefail

# Directories
CLAUDE_DIR="$HOME/.claude/projects"
ARCHIVE_DIR="$HOME/Library/Application Support/mindbase/conversations/claude-code"
LOG_FILE="/tmp/claude-code-collector.log"

# Logging
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

# Archive threshold (days)
ARCHIVE_THRESHOLD_DAYS=${1:-90}

log "🔍 Starting Claude Code conversation collection"
log "📂 Source: $CLAUDE_DIR"
log "📦 Archive: $ARCHIVE_DIR"
log "⏰ Threshold: ${ARCHIVE_THRESHOLD_DAYS} days"

# Create archive directories
mkdir -p "$ARCHIVE_DIR"/{agiletec,mkk,ec-cloud-app,global}

# Count conversations
total_files=$(find "$CLAUDE_DIR" -name "*.jsonl" -type f 2>/dev/null | wc -l | xargs)
log "📊 Found $total_files conversation files"

# Collect old conversations (>N days)
old_files=$(find "$CLAUDE_DIR" -name "*.jsonl" -type f -mtime +"$ARCHIVE_THRESHOLD_DAYS" 2>/dev/null)
old_count=$(echo "$old_files" | grep -c "\.jsonl" || echo "0")

log "🗄️  Archiving $old_count conversations (>$ARCHIVE_THRESHOLD_DAYS days old)"

# Archive old conversations by project
for file in $old_files; do
    # Extract project name from path
    project_dir=$(dirname "$file")
    project_name=$(basename "$project_dir")

    # Determine target directory
    case "$project_name" in
        *agiletec*)
            target_dir="$ARCHIVE_DIR/agiletec"
            ;;
        *mkk*)
            target_dir="$ARCHIVE_DIR/mkk"
            ;;
        *ec-cloud*)
            target_dir="$ARCHIVE_DIR/ec-cloud-app"
            ;;
        *)
            target_dir="$ARCHIVE_DIR/global"
            ;;
    esac

    # Move file to archive
    filename=$(basename "$file")
    mv "$file" "$target_dir/$filename"
    log "  ✅ Archived: $filename → $(basename "$target_dir")/"
done

# Summary statistics
agiletec_count=$(ls -1 "$ARCHIVE_DIR/agiletec" 2>/dev/null | wc -l | xargs)
mkk_count=$(ls -1 "$ARCHIVE_DIR/mkk" 2>/dev/null | wc -l | xargs)
ec_count=$(ls -1 "$ARCHIVE_DIR/ec-cloud-app" 2>/dev/null | wc -l | xargs)
global_count=$(ls -1 "$ARCHIVE_DIR/global" 2>/dev/null | wc -l | xargs)
remaining_count=$(find "$CLAUDE_DIR" -name "*.jsonl" -type f 2>/dev/null | wc -l | xargs)

log "📊 Archive Summary:"
log "  agiletec: $agiletec_count files"
log "  mkk: $mkk_count files"
log "  ec-cloud-app: $ec_count files"
log "  global: $global_count files"
log "  Total archived: $old_count files"
log "  Remaining in .claude: $remaining_count files"
log "✅ Collection complete"
