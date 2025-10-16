# Contributing to MindBase

Thank you for your interest in contributing to MindBase! This document provides guidelines and instructions for contributing.

## 🚀 Getting Started

### Prerequisites

- Docker and Docker Compose (or OrbStack)
- pnpm (for TypeScript workflows)
- Git
- Basic knowledge of Python (FastAPI) and TypeScript

### Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/kazukinakai/mindbase.git
   cd mindbase
   ```

2. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env if needed (defaults work for local development)
   ```

3. **Start Docker services**
   ```bash
   make up              # Start all services
   make model-pull      # Download Ollama model (first time only, ~4.7GB)
   make migrate         # Run database migrations
   make health          # Verify services are running
   ```

4. **Verify installation**
   ```bash
   make ps              # Check container status
   curl http://localhost:18002/health  # API health check
   ```

## 🏗️ Project Structure

```
mindbase/
├── app/                 # FastAPI backend
│   ├── api/            # API routes
│   ├── crud/           # Database operations
│   ├── models/         # SQLAlchemy models
│   └── schemas/        # Pydantic schemas
├── collectors/         # Python conversation collectors
├── src/                # TypeScript processors/generators
├── scripts/            # Shell scripts
├── supabase/           # Database migrations
├── templates/          # Article generation templates
└── docs/               # Additional documentation

Data (NOT in Git):
~/Library/Application Support/mindbase/conversations/  # Archived conversations
```

## 🧪 Testing

### Python Tests

```bash
# Enter API container
make api-shell

# Inside container
pytest tests/ -v                          # All tests
pytest tests/test_collectors.py -v       # Specific test file
pytest tests/ -k "test_embedding" -v     # Pattern matching
pytest tests/ --cov=app --cov-report=html # Coverage report
```

### Code Quality

```bash
# Inside api-shell
black app/ collectors/              # Format code
ruff check app/ collectors/         # Lint
ruff check app/ collectors/ --fix   # Auto-fix
mypy app/ collectors/               # Type check
```

### TypeScript Tests

```bash
pnpm test                # Run TypeScript tests
pnpm lint                # Run ESLint
pnpm typecheck           # Run TypeScript compiler check
```

## 📝 Development Workflow

### Feature Development

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Follow existing code style
   - Add tests for new functionality
   - Update documentation as needed

3. **Test your changes**
   ```bash
   make test            # Run all tests
   make lint            # Check code quality
   ```

4. **Commit your changes**
   ```bash
   git add .
   git commit -m "feat: add new feature description"
   ```

   Follow [Conventional Commits](https://www.conventionalcommits.org/):
   - `feat:` New feature
   - `fix:` Bug fix
   - `docs:` Documentation only
   - `style:` Code style changes (formatting)
   - `refactor:` Code refactoring
   - `test:` Adding tests
   - `chore:` Maintenance tasks

5. **Push to your fork**
   ```bash
   git push origin feature/your-feature-name
   ```

6. **Create a Pull Request**
   - Provide clear description of changes
   - Reference related issues
   - Ensure CI passes

## 🎯 Contribution Areas

### High Priority

- **Data Source Collectors**: Add support for new platforms (Slack, Gmail, Google Docs)
- **MCP Server Integration**: Airis Gateway integration for conversation storage/search
- **Performance Optimization**: Embedding generation, database queries
- **Testing**: Increase test coverage for collectors and API endpoints

### Documentation

- Improve API documentation
- Add usage examples
- Tutorial for custom collectors
- Troubleshooting guides

### Bug Fixes

- Check [Issues](https://github.com/kazukinakai/mindbase/issues) for open bugs
- Report new bugs with reproduction steps

## 📐 Code Style Guidelines

### Python

- Follow PEP 8
- Use type hints for all functions
- Async/await for I/O operations
- Pydantic for validation
- SQLAlchemy for database operations

```python
async def store_conversation(
    conversation: ConversationCreate,
    db: AsyncSession
) -> Conversation:
    """Store conversation with embedding generation."""
    # Implementation
```

### TypeScript

- Use ESM modules
- Async/await for I/O
- Type annotations required
- Clear function documentation

```typescript
async function extractModules(
  conversations: Conversation[]
): Promise<Module[]> {
  // Implementation
}
```

### Naming Conventions

- Python: `snake_case` for functions, variables
- TypeScript: `camelCase` for functions, `PascalCase` for classes
- Files: `kebab-case` for scripts, match language conventions otherwise

## 🔍 Review Process

1. **Automated Checks**: CI runs tests and linters
2. **Code Review**: Maintainer reviews code quality and design
3. **Discussion**: Address feedback and questions
4. **Merge**: Once approved, maintainer merges PR

## 🐛 Reporting Bugs

Use [GitHub Issues](https://github.com/kazukinakai/mindbase/issues) with:

- Clear, descriptive title
- Steps to reproduce
- Expected vs actual behavior
- Environment details (OS, Docker version)
- Logs or error messages

## 💡 Suggesting Features

- Check existing issues first
- Describe use case and benefits
- Consider implementation approach
- Open to discussion before implementation

## 📄 License

By contributing, you agree that your contributions will be licensed under the MIT License.

## 🤝 Community

- Be respectful and constructive
- Help others when possible
- Share knowledge and learnings

## 📞 Contact

- Issues: [GitHub Issues](https://github.com/kazukinakai/mindbase/issues)
- Discussions: [GitHub Discussions](https://github.com/kazukinakai/mindbase/discussions)
- Email: [your-email@example.com]

Thank you for contributing to MindBase! 🎉
