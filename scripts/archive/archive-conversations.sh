#!/bin/bash
set -euo pipefail

# Claude Code Optimization Script
# Moves conversations older than 7 days to archive, keeps active dir clean

CLAUDE_PROJECTS="$HOME/.claude/projects"
BACKUP_ROOT="$HOME/Library/Application Support/mindbase"
ARCHIVE_BY_DATE="$BACKUP_ROOT/conversations/claude-code/by-date"
ARCHIVE_BY_PROJECT="$BACKUP_ROOT/conversations/claude-code/by-project"
LOG_DIR="$HOME/github/mindbase/logs"
LOG_FILE="$LOG_DIR/archive-$(date +%Y%m%d).log"

# Create directories
mkdir -p "$ARCHIVE_BY_DATE"
mkdir -p "$ARCHIVE_BY_PROJECT"
mkdir -p "$LOG_DIR"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "=== Claude Code Optimization Started ==="

# Check size before optimization
BEFORE_SIZE=$(du -sh "$CLAUDE_PROJECTS" | cut -f1)
log "Claude projects size before: $BEFORE_SIZE"

# Find and archive old conversations (>7 days)
ARCHIVED_COUNT=0
TOTAL_SIZE=0

# Use process substitution instead of pipe to preserve variables
while IFS= read -r file; do
    # Extract project directory name
    PROJECT_DIR=$(basename "$(dirname "$file")")
    FILE_NAME=$(basename "$file")

    # Get file date
    FILE_DATE=$(date -r "$file" +%Y/%m/%d)

    # Create archive directories
    DATE_ARCHIVE="$ARCHIVE_BY_DATE/$FILE_DATE/$PROJECT_DIR"

    # Extract project name from directory (remove -Users-kazuki-github- prefix)
    PROJECT_NAME=$(echo "$PROJECT_DIR" | sed 's/-Users-kazuki-github-//')
    PROJECT_ARCHIVE="$ARCHIVE_BY_PROJECT/$PROJECT_NAME/$(date -r "$file" +%Y-%m)"

    mkdir -p "$DATE_ARCHIVE"
    mkdir -p "$PROJECT_ARCHIVE"

    # Get file size
    FILE_SIZE=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null)

    # Move to both archives (hard link to save space)
    mv "$file" "$DATE_ARCHIVE/"
    ln "$DATE_ARCHIVE/$FILE_NAME" "$PROJECT_ARCHIVE/" 2>/dev/null || cp "$DATE_ARCHIVE/$FILE_NAME" "$PROJECT_ARCHIVE/"

    log "Archived: $PROJECT_DIR/$FILE_NAME ($(numfmt --to=iec $FILE_SIZE 2>/dev/null || echo $FILE_SIZE bytes))"

    ARCHIVED_COUNT=$((ARCHIVED_COUNT + 1))
    TOTAL_SIZE=$((TOTAL_SIZE + FILE_SIZE))
done < <(find "$CLAUDE_PROJECTS" -name "*.jsonl" -mtime +7)

# Check size after optimization
AFTER_SIZE=$(du -sh "$CLAUDE_PROJECTS" | cut -f1)
log "Claude projects size after: $AFTER_SIZE"

# Format total size
TOTAL_SIZE_FORMATTED=$(numfmt --to=iec $TOTAL_SIZE 2>/dev/null || echo "$TOTAL_SIZE bytes")

log "Archived $ARCHIVED_COUNT conversations ($TOTAL_SIZE_FORMATTED)"

# Update statistics
mkdir -p "$HOME/github/mindbase/logs"
cat > "$LOG_DIR/stats.json" << EOF
{
  "last_optimization": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "size_before": "$BEFORE_SIZE",
  "size_after": "$AFTER_SIZE",
  "archived_count": $ARCHIVED_COUNT,
  "archived_size": "$TOTAL_SIZE_FORMATTED"
}
EOF

log "Statistics saved to $LOG_DIR/stats.json"
log "=== Optimization Completed Successfully ==="
