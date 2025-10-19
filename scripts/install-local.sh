#!/bin/bash
# Local installation script for MindBase
# This mimics what Homebrew formula will do

set -e

echo "🔧 MindBase Local Installation"
echo "=============================="

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Installation directory
INSTALL_DIR="${INSTALL_DIR:-$HOME/.local/share/mindbase}"
BIN_DIR="${BIN_DIR:-$HOME/.local/bin}"

echo ""
echo "📂 Installation directories:"
echo "   Install: $INSTALL_DIR"
echo "   Bin: $BIN_DIR"

# 1. Check dependencies
echo ""
echo "1️⃣ Checking dependencies..."

if ! command -v brew &> /dev/null; then
    echo -e "${RED}❌ Homebrew not found${NC}"
    echo "   Install from: https://brew.sh"
    exit 1
fi
echo -e "${GREEN}✅ Homebrew${NC}"

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 not found${NC}"
    echo "   Install with: brew install python@3.12"
    exit 1
fi
echo -e "${GREEN}✅ Python 3${NC}"

if ! command -v psql &> /dev/null; then
    echo -e "${YELLOW}⚠️ PostgreSQL not found${NC}"
    echo "   Installing..."
    brew install postgresql@16
fi
echo -e "${GREEN}✅ PostgreSQL${NC}"

if ! command -v ollama &> /dev/null; then
    echo -e "${YELLOW}⚠️ Ollama not found${NC}"
    echo "   Installing..."
    brew install ollama
fi
echo -e "${GREEN}✅ Ollama${NC}"

if ! command -v pnpm &> /dev/null; then
    echo -e "${YELLOW}⚠️ pnpm not found${NC}"
    echo "   Installing..."
    npm install -g pnpm
fi
echo -e "${GREEN}✅ pnpm${NC}"

# 2. Create directories
echo ""
echo "2️⃣ Creating directories..."
mkdir -p "$INSTALL_DIR"
mkdir -p "$BIN_DIR"
mkdir -p "$HOME/Library/Application Support/mindbase"
echo -e "${GREEN}✅ Directories created${NC}"

# 3. Copy files
echo ""
echo "3️⃣ Installing files..."
cp -r . "$INSTALL_DIR/"
echo -e "${GREEN}✅ Files copied${NC}"

# 4. Create virtual environment
echo ""
echo "4️⃣ Creating Python virtual environment..."
cd "$INSTALL_DIR"
python3 -m venv venv
source venv/bin/activate
echo -e "${GREEN}✅ Virtual environment created${NC}"

# 5. Install Python dependencies
echo ""
echo "5️⃣ Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
echo -e "${GREEN}✅ Python dependencies installed${NC}"

# 6. Install TypeScript dependencies
echo ""
echo "6️⃣ Installing TypeScript dependencies..."
pnpm install
echo -e "${GREEN}✅ TypeScript dependencies installed${NC}"

# 7. Create wrapper script
echo ""
echo "7️⃣ Creating executable wrapper..."
cat > "$BIN_DIR/mindbase" << 'EOF'
#!/bin/bash
# MindBase wrapper script

INSTALL_DIR="${INSTALL_DIR:-$HOME/.local/share/mindbase}"
export PATH="$INSTALL_DIR/venv/bin:$PATH"
export DATABASE_URL="${DATABASE_URL:-postgresql+asyncpg://$USER@localhost:5432/mindbase}"
export OLLAMA_URL="${OLLAMA_URL:-http://localhost:11434}"
export API_PORT="${API_PORT:-18002}"
export DATA_DIR="${DATA_DIR:-$HOME/Library/Application Support/mindbase}"

exec "$INSTALL_DIR/venv/bin/python" "$INSTALL_DIR/bin/mindbase" "$@"
EOF
chmod +x "$BIN_DIR/mindbase"
echo -e "${GREEN}✅ Wrapper script created${NC}"

# 8. Setup database
echo ""
echo "8️⃣ Setting up database..."
createdb mindbase 2>/dev/null || echo "   (Database already exists)"
psql mindbase -c "CREATE EXTENSION IF NOT EXISTS vector;" 2>/dev/null || true
echo -e "${GREEN}✅ Database setup${NC}"

# 9. Pull Ollama model
echo ""
echo "9️⃣ Pulling Ollama embedding model..."
echo "   This may take a few minutes (~4.7GB)..."
ollama pull qwen3-embedding:8b
echo -e "${GREEN}✅ Ollama model ready${NC}"

# 10. Run migrations
echo ""
echo "🔟 Running database migrations..."
cd "$INSTALL_DIR"
source venv/bin/activate
alembic upgrade head
echo -e "${GREEN}✅ Migrations complete${NC}"

# Done!
echo ""
echo -e "${GREEN}✨ Installation complete!${NC}"
echo ""
echo "Next steps:"
echo "  1. Add to PATH (if not already): export PATH=\"$BIN_DIR:\$PATH\""
echo "  2. Start service: mindbase serve"
echo "  3. Check health: mindbase health"
echo ""
echo "Or create a launchd service for auto-start:"
echo "  cp scripts/com.mindbase.plist ~/Library/LaunchAgents/"
echo "  launchctl load ~/Library/LaunchAgents/com.mindbase.plist"
