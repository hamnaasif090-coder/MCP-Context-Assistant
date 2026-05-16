---
title: Engineering Standards & Best Practices
category: Engineering
author: CTO Office
last_updated: 2024-02-01
---

# Engineering Standards & Best Practices

This document defines the engineering standards all teams are expected to follow.

## Code Quality

### Language Standards
- **Python**: 3.11+, follow PEP 8, use type hints everywhere, black for formatting
- **TypeScript**: Strict mode enabled, ESLint + Prettier, no `any` types
- **SQL**: Uppercase keywords, one statement per line, always use parameterized queries

### Code Review Requirements
All code must pass review before merging to main:
- At least 2 approvals required for core services
- At least 1 approval required for non-critical changes
- CI/CD pipeline must be green
- No merge conflicts
- Test coverage must not drop below 80%

### Documentation
Every module, class, and public function must have a docstring. READMEs are required for:
- All microservices
- Internal libraries
- Infrastructure components

## Git Workflow

We use trunk-based development:
1. Branch from `main` with naming: `feat/`, `fix/`, `chore/`, `docs/`
2. Keep branches short-lived (max 3 days)
3. Squash commits before merging
4. Delete branches after merge
5. Never force-push to main

Commit message format:
```
type(scope): short description

Longer explanation if needed. Reference issues with #123.
```

## Testing Standards

### Unit Tests
- Required for all business logic
- Use pytest for Python, Jest for TypeScript
- Mock external dependencies
- Tests live in `/tests` directory mirroring `/src`

### Integration Tests
- Required for all API endpoints
- Use TestClient (FastAPI) or Supertest (Express)
- Must run in under 5 minutes total

### End-to-End Tests
- Playwright for browser testing
- Run nightly in CI, not on every PR
- Cover all critical user journeys

## Infrastructure & Deployment

### Containerization
All services must be containerized:
```dockerfile
# Use specific versions, not latest
FROM python:3.11-slim
# Run as non-root user
RUN adduser --disabled-password appuser
USER appuser
```

### CI/CD Pipeline
We use GitHub Actions. Every PR triggers:
1. Lint + format check
2. Unit tests
3. Integration tests
4. Security scan (Snyk)
5. Docker build

### Environments
| Environment | Branch | URL | Auto-Deploy |
|-------------|--------|-----|-------------|
| Development | any PR | pr-{n}.dev.company.com | Yes |
| Staging | main | staging.company.com | Yes |
| Production | tags (v*) | company.com | Manual approval |

## Security Requirements

- Never commit secrets to git — use environment variables
- All APIs must require authentication
- Use HTTPS everywhere; no HTTP in production
- Dependency security scans run weekly
- OWASP Top 10 checklist for all new services

## Incident Response

### Severity Levels
- **SEV1**: Complete outage — page on-call immediately, 15-min response SLA
- **SEV2**: Degraded service — 1-hour response SLA
- **SEV3**: Minor issue — next business day

### On-Call Rotation
On-call rotates weekly. The current schedule is in PagerDuty. On-call engineers must:
- Respond within 15 minutes during off-hours for SEV1
- Write a post-mortem within 48 hours of any SEV1/SEV2

## Observability

All services must emit:
- **Logs**: Structured JSON to CloudWatch
- **Metrics**: Business metrics via Prometheus + Grafana
- **Traces**: Distributed tracing via AWS X-Ray
- **Alerts**: PagerDuty for SEV1, Slack for SEV2/3
