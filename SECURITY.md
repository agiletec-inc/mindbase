# Security Policy

## Supported Versions

Currently supported versions of MindBase:

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

As this project is in early development, we support only the latest version. Security updates will be released promptly for critical vulnerabilities.

## Reporting a Vulnerability

We take the security of MindBase seriously. If you discover a security vulnerability, please report it responsibly.

### How to Report

**DO NOT** open a public issue for security vulnerabilities.

Instead, please email us at:
- **Email**: security@agiletec.jp
- **Subject**: `[SECURITY] MindBase Vulnerability Report`

### What to Include

Please provide the following information:

1. **Description**: Clear description of the vulnerability
2. **Impact**: Potential impact and attack scenario
3. **Reproduction**: Step-by-step instructions to reproduce
4. **Environment**:
   - Operating system
   - Docker version
   - MindBase version
   - Any relevant configuration
5. **Proof of Concept**: Code or screenshots (if applicable)
6. **Suggested Fix**: If you have ideas for mitigation

### Response Timeline

- **Initial Response**: Within 48 hours of report
- **Status Update**: Within 7 days with assessment
- **Fix Timeline**:
  - Critical: 7-14 days
  - High: 14-30 days
  - Medium: 30-60 days
  - Low: Next scheduled release

### Disclosure Policy

- **Coordinated Disclosure**: We request 90 days before public disclosure
- **Credit**: We will credit researchers in security advisories (unless you prefer anonymity)
- **Updates**: We will keep you informed throughout the process

## Security Considerations

### Data Privacy

**Conversation Data Isolation**:
- Conversation data stored in `~/Library/Application Support/mindbase/`
- **NOT** included in Git repository
- Excluded from Docker images
- Local processing only (no external API calls for embeddings)

**API Keys and Secrets**:
- Use environment variables (`.env` files)
- **NEVER** commit `.env` files to Git
- Docker secrets recommended for production
- Follow `.env.example` for configuration

### Docker Security

**Container Isolation**:
- All services run in isolated Docker containers
- No privileged containers
- Minimal base images
- Regular dependency updates

**Network Security**:
- Services communicate via internal Docker network
- Only necessary ports exposed to host
- No default remote access

### Database Security

**PostgreSQL**:
- Default credentials for development only
- Change passwords in production
- Use strong passwords (16+ characters)
- Enable SSL/TLS for production deployments

**Data Encryption**:
- Conversations stored as embeddings (1024-dimensional vectors)
- Database backups should be encrypted
- Consider encrypting data directory at rest

### API Security

**FastAPI Backend**:
- Input validation with Pydantic schemas
- SQL injection prevention via SQLAlchemy ORM
- Rate limiting recommended for production
- CORS configuration for allowed origins

**Authentication**:
- Currently designed for local use only
- Implement authentication before exposing to network
- Use JWT tokens or API keys for production

### Dependencies

**Regular Updates**:
- Monitor dependency vulnerabilities
- Update Python packages: `pip list --outdated`
- Update Node packages: `pnpm outdated`
- Review Docker base image updates

**Known Dependencies**:
- Python: FastAPI, SQLAlchemy, asyncpg, pydantic
- TypeScript: Node.js, tsx
- Docker: PostgreSQL 17, Ollama
- Embedding Model: qwen3-embedding:8b (Ollama)

## Security Best Practices

### Development

1. **Code Review**: All changes reviewed before merge
2. **Static Analysis**: Use `ruff`, `mypy` for Python
3. **Dependency Scanning**: Regular security audits
4. **Least Privilege**: Run services with minimal permissions

### Production Deployment

1. **Change Default Credentials**: Update all passwords
2. **Enable HTTPS**: Use TLS for API endpoints
3. **Firewall Configuration**: Restrict network access
4. **Regular Backups**: Automated, encrypted backups
5. **Monitoring**: Log and monitor security events
6. **Updates**: Keep all dependencies current

### Data Handling

1. **Personal Information**: Review conversations for PII before processing
2. **Data Retention**: Implement retention policies
3. **Access Control**: Limit who can access conversation data
4. **Compliance**: Follow applicable regulations (GDPR, etc.)

## Known Limitations

### Current Security Status

- **Local Development Focus**: Designed for single-user local use
- **No Built-in Authentication**: Not production-ready without authentication
- **Default Credentials**: Development defaults must be changed for production
- **Network Exposure**: Should not be exposed to internet without hardening

### Future Security Enhancements

- User authentication and authorization
- API rate limiting
- Audit logging
- Encrypted backups
- RBAC (Role-Based Access Control)
- Security headers and CSRF protection

## Resources

- [OWASP Top Ten](https://owasp.org/www-project-top-ten/)
- [Docker Security Best Practices](https://docs.docker.com/engine/security/)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [PostgreSQL Security](https://www.postgresql.org/docs/current/security.html)

## Vulnerability Disclosure History

No vulnerabilities have been publicly disclosed at this time.

---

**Last Updated**: 2025-10-16

Thank you for helping keep MindBase secure!
