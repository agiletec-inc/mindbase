class Mindbase < Formula
  desc "AI conversation knowledge management system with MCP integration"
  homepage "https://github.com/agiletec-inc/mindbase"
  url "https://github.com/agiletec-inc/mindbase/archive/refs/tags/v1.0.0.tar.gz"
  sha256 "" # Will be calculated on release
  license "MIT"
  head "https://github.com/agiletec-inc/mindbase.git", branch: "master"

  depends_on "python@3.12"
  depends_on "postgresql@16"
  depends_on "ollama"
  depends_on "node"

  resource "pnpm" do
    url "https://registry.npmjs.org/pnpm/-/pnpm-9.0.0.tgz"
    sha256 "" # Will be calculated
  end

  def install
    # Python virtual environment
    venv = libexec/"venv"
    system "python3.12", "-m", "venv", venv
    system venv/"bin/pip", "install", "--upgrade", "pip"
    system venv/"bin/pip", "install", "-r", "requirements.txt"

    # TypeScript dependencies
    system "npm", "install", "-g", "pnpm"
    system "pnpm", "install", "--prod", "--frozen-lockfile"

    # Install all files to libexec
    libexec.install Dir["*"]

    # Create wrapper script
    (bin/"mindbase").write_env_script libexec/"bin/mindbase",
      PATH:         "#{venv}/bin:#{libexec}/node_modules/.bin:$PATH",
      DATABASE_URL: "postgresql+asyncpg://#{ENV.fetch("USER")}@localhost:5432/mindbase",
      OLLAMA_URL:   "http://localhost:11434",
      API_PORT:     "18002",
      DATA_DIR:     "#{ENV.fetch("HOME")}/Library/Application Support/mindbase"
  end

  def post_install
    # Create data directory
    (var/"mindbase").mkpath
    config_dir = Pathname.new(ENV.fetch("HOME"))/"Library/Application Support/mindbase"
    config_dir.mkpath

    # PostgreSQL setup
    system "createdb", "mindbase" unless quiet_system "psql", "-lqt", "|", "cut", "-d", "|", "-f", "1", "|", "grep", "-qw", "mindbase"
    system "psql", "mindbase", "-c", "CREATE EXTENSION IF NOT EXISTS vector;"

    # Ollama model
    ohai "Pulling Ollama embedding model (qwen3-embedding:8b)..."
    ohai "This may take a few minutes (~4.7GB download)..."
    system "ollama", "pull", "qwen3-embedding:8b"

    # Database migrations
    ohai "Running database migrations..."
    system libexec/"venv/bin/alembic", "upgrade", "head"

    ohai "Setup complete!"
    ohai "Start service with: brew services start mindbase"
    ohai "Or run manually: mindbase serve"
  end

  service do
    run [opt_bin/"mindbase", "serve"]
    working_dir var/"mindbase"
    keep_alive true
    log_path var/"log/mindbase.log"
    error_log_path var/"log/mindbase.error.log"
    environment_variables DATABASE_URL: "postgresql+asyncpg://#{ENV.fetch("USER")}@localhost:5432/mindbase",
                          OLLAMA_URL:   "http://localhost:11434",
                          API_PORT:     "18002",
                          DATA_DIR:     "#{ENV.fetch("HOME")}/Library/Application Support/mindbase"
  end

  test do
    system bin/"mindbase", "version"
    assert_match "MindBase v1.0.0", shell_output("#{bin}/mindbase version")

    # Test health (requires service running)
    # system bin/"mindbase", "health"
  end
end
