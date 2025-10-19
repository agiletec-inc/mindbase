# MindBase Installation Guide

Complete installation guide for MindBase - AI Conversation Knowledge Management System with MCP integration.

## Quick Install (Recommended)

### Using Homebrew (macOS)

```bash
# Add MindBase tap
brew tap agiletec-inc/mindbase

# Install MindBase
brew install mindbase

# Setup (one-time: creates DB, pulls Ollama model)
mindbase setup

# Start service
brew services start mindbase

# Verify installation
mindbase health
curl http://localhost:18002/health
```

**What gets installed:**
- Python 3.12 virtual environment
- PostgreSQL 16 + pgvector extension
- Ollama embedding service (GPU-enabled)
- FastAPI backend (port 18002)
- TypeScript dependencies
- Database migrations

**Data locations:**
- Config: `~/Library/Application Support/mindbase/`
- Logs: `~/Library/Logs/mindbase.log`
- Database: Local PostgreSQL (`mindbase` database)

## Manual Installation

### Prerequisites

```bash
# Install dependencies
brew install python@3.12 postgresql@16 ollama node

# Install pnpm
npm install -g pnpm

# Start PostgreSQL
brew services start postgresql@16

# Start Ollama
brew services start ollama
```

### Clone and Install

```bash
# Clone repository
git clone https://github.com/agiletec-inc/mindbase.git
cd mindbase

# Run installation script
bash scripts/install-local.sh
```

The script will:
1. Create virtual environment at `~/.local/share/mindbase/venv`
2. Install Python dependencies
3. Install TypeScript dependencies
4. Create database with pgvector extension
5. Pull Ollama embedding model (qwen3-embedding:8b, ~4.7GB)
6. Run database migrations
7. Create executable wrapper at `~/.local/bin/mindbase`

### Add to PATH

```bash
# Add to ~/.zshrc or ~/.bashrc
export PATH="$HOME/.local/bin:$PATH"

# Reload shell
source ~/.zshrc
```

## Configuration

### Environment Variables

Production defaults (`~/.local/share/mindbase/.env`):

```bash
# Database
DATABASE_URL=postgresql+asyncpg://$(whoami)@localhost:5432/mindbase

# Ollama
OLLAMA_URL=http://localhost:11434
EMBEDDING_MODEL=qwen3-embedding:8b
EMBEDDING_DIMENSIONS=1024

# API
API_PORT=18002
DEBUG=false

# Data directory
DATA_DIR=${HOME}/Library/Application Support/mindbase
```

### MCP Server Setup

Add to Claude Desktop config (`~/.config/claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "mindbase": {
      "command": "mindbase",
      "args": ["serve"],
      "env": {
        "DATABASE_URL": "postgresql+asyncpg://YOUR_USERNAME@localhost:5432/mindbase",
        "OLLAMA_URL": "http://localhost:11434"
      }
    }
  }
}
```

Replace `YOUR_USERNAME` with your macOS username.

## Usage

### Start Service

```bash
# Foreground (logs to console)
mindbase serve

# Background (via launchd)
brew services start mindbase

# Background (manual launchd)
cp scripts/com.mindbase.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.mindbase.plist
```

### Verify Running

```bash
# Health check
mindbase health

# Or via curl
curl http://localhost:18002/health

# Expected response:
{
  "status": "healthy",
  "database": "connected",
  "ollama": "available"
}
```

### View Logs

```bash
# Homebrew service logs
tail -f ~/Library/Logs/mindbase.log
tail -f ~/Library/Logs/mindbase.error.log

# Launchd logs
tail -f ~/Library/Logs/com.mindbase.stdout.log
tail -f ~/Library/Logs/com.mindbase.stderr.log
```

### API Documentation

Open in browser: http://localhost:18002/docs

Interactive Swagger UI for testing API endpoints.

## Updating

### Homebrew Update

```bash
# Update tap
brew update

# Upgrade MindBase
brew upgrade mindbase

# Restart service
brew services restart mindbase
```

### Manual Update

```bash
cd /path/to/mindbase
git pull origin main
bash scripts/install-local.sh
brew services restart mindbase
```

## Uninstallation

### Homebrew Uninstall

```bash
# Stop service
brew services stop mindbase

# Uninstall
brew uninstall mindbase

# Remove data (optional)
rm -rf ~/Library/Application\ Support/mindbase
rm -rf ~/Library/Logs/mindbase*

# Drop database (optional)
dropdb mindbase
```

### Manual Uninstall

```bash
# Remove installation
rm -rf ~/.local/share/mindbase
rm ~/.local/bin/mindbase

# Remove launchd service
launchctl unload ~/Library/LaunchAgents/com.mindbase.plist
rm ~/Library/LaunchAgents/com.mindbase.plist

# Remove data
rm -rf ~/Library/Application\ Support/mindbase
rm -rf ~/Library/Logs/mindbase*

# Drop database
dropdb mindbase
```

## Development Setup

For contributing to MindBase development, see [CLAUDE.md](CLAUDE.md) for Docker development environment setup.

**TL;DR:**

```bash
# Clone repository
git clone https://github.com/agiletec-inc/mindbase.git
cd mindbase

# Start Docker development environment (port 18003)
make init

# Development and production run simultaneously without conflicts
# Production: http://localhost:18002 (brew install)
# Development: http://localhost:18003 (docker)
```

## Troubleshooting

### PostgreSQL Connection Failed

```bash
# Check if PostgreSQL is running
brew services list | grep postgresql

# Start PostgreSQL
brew services start postgresql@16

# Check database exists
psql -l | grep mindbase

# Create database if missing
createdb mindbase
psql mindbase -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### Ollama Model Not Found

```bash
# Check Ollama is running
brew services list | grep ollama

# Pull embedding model
ollama pull qwen3-embedding:8b

# Verify model
ollama list | grep qwen3-embedding
```

### Port Already in Use

```bash
# Check what's using port 18002
lsof -i :18002

# Kill process (if needed)
kill -9 <PID>

# Or change port
export API_PORT=18004
mindbase serve
```

### Permission Denied

```bash
# Fix ownership
sudo chown -R $(whoami) ~/.local/share/mindbase
sudo chown -R $(whoami) ~/Library/Application\ Support/mindbase

# Fix permissions
chmod +x ~/.local/bin/mindbase
```

## System Requirements

- **OS**: macOS 12.0 or later
- **CPU**: Any (M1/M2/M3 recommended for GPU acceleration)
- **RAM**: 8GB minimum, 16GB recommended
- **Disk**: ~5GB free space
  - PostgreSQL: ~100MB
  - Ollama model: ~4.7GB
  - Application: ~200MB

## Support

- **Documentation**: [CLAUDE.md](CLAUDE.md)
- **Issues**: [GitHub Issues](https://github.com/agiletec-inc/mindbase/issues)
- **Discussions**: [GitHub Discussions](https://github.com/agiletec-inc/mindbase/discussions)
