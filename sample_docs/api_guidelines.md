---
title: Internal API Guidelines
category: Engineering
author: Platform Team
last_updated: 2024-04-01
---

# Internal API Guidelines

This document covers standards for building and consuming internal APIs.

## REST API Design Principles

### URL Structure
- Use nouns, not verbs: `/users` not `/getUsers`
- Plural resource names: `/orders`, `/products`
- Nested resources for relationships: `/users/{id}/orders`
- Kebab-case for multi-word paths: `/order-items`

### HTTP Methods
| Method | Usage | Idempotent |
|--------|-------|------------|
| GET | Read resources | Yes |
| POST | Create resources | No |
| PUT | Replace resource | Yes |
| PATCH | Partial update | No |
| DELETE | Remove resource | Yes |

### Status Codes
Always use semantically correct status codes:
- `200 OK` – successful GET, PUT, PATCH
- `201 Created` – successful POST with resource creation
- `204 No Content` – successful DELETE
- `400 Bad Request` – validation error (include error details)
- `401 Unauthorized` – missing or invalid auth token
- `403 Forbidden` – authenticated but lacks permission
- `404 Not Found` – resource doesn't exist
- `409 Conflict` – duplicate resource or state conflict
- `422 Unprocessable Entity` – semantic validation failure
- `429 Too Many Requests` – rate limit exceeded
- `500 Internal Server Error` – unexpected server error

### Versioning
All APIs must be versioned via URL path: `/api/v1/`, `/api/v2/`
- Never break v1 once published
- Deprecation notice minimum: 6 months
- Include `Deprecation` header for sunset APIs

## Request & Response Format

### Request Headers
```
Content-Type: application/json
Authorization: Bearer <token>
X-Request-ID: <uuid>          # for tracing
X-Client-Version: 1.2.3       # client app version
```

### Standard Response Envelope
```json
{
  "data": { },
  "meta": {
    "request_id": "uuid",
    "timestamp": "2024-01-15T10:30:00Z",
    "version": "v1"
  },
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 150,
    "total_pages": 8
  }
}
```

### Error Response Format
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": [
      { "field": "email", "message": "Invalid email format" }
    ],
    "request_id": "uuid",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

## Authentication

### JWT Authentication
All internal APIs use JWT Bearer tokens:
```
Authorization: Bearer eyJhbGciOiJSUzI1NiJ9...
```
- Tokens expire after 1 hour
- Refresh tokens valid for 30 days
- Use the auth service at `auth.internal.company.com`

### Service-to-Service Auth
Internal services communicate using service account tokens:
- Request from the platform team via `#platform-eng` Slack
- Rotate every 90 days
- Never hardcode in source — use Vault or environment variables

### API Keys (External Partners)
For external integrations:
- Generate via admin dashboard at `admin.company.com/api-keys`
- Keys are prefixed: `ck_live_` (production), `ck_test_` (sandbox)
- Rate limited by default (see Rate Limiting section)

## Rate Limiting

| Tier | Limit | Window |
|------|-------|--------|
| Anonymous | 10 | 1 minute |
| Authenticated | 1,000 | 1 hour |
| Partner | 10,000 | 1 hour |
| Internal Service | Unlimited | — |

Rate limit headers in every response:
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 943
X-RateLimit-Reset: 1705316400
Retry-After: 3600   # only on 429
```

## Pagination

Use cursor-based pagination for large datasets:
```
GET /api/v1/events?cursor=eyJpZCI6MTAwfQ&limit=50
```

Response:
```json
{
  "data": [...],
  "pagination": {
    "next_cursor": "eyJpZCI6MTUwfQ",
    "prev_cursor": "eyJpZCI6NTB9",
    "has_more": true
  }
}
```

For small, bounded lists (< 1000 items), offset pagination is acceptable:
```
GET /api/v1/categories?page=2&per_page=20
```

## API Documentation

Every API must have:
1. OpenAPI 3.0 spec (`openapi.yaml` in repo root)
2. Example requests and responses for every endpoint
3. Authentication requirements documented
4. Error codes and descriptions listed
5. Changelog for version differences

Auto-generate docs using FastAPI's built-in `/docs` or Swagger UI.
Publish to internal developer portal at `developers.internal.company.com`.

## Webhooks

For event-driven integrations:
- Use HTTPS endpoints only
- Sign payloads with HMAC-SHA256: `X-Signature: sha256=<hash>`
- Retry with exponential backoff (3 attempts: 1min, 5min, 30min)
- Deliver within 30 seconds; consumers must respond with 2xx within 10s
- Include `X-Event-ID` for idempotent processing

Webhook payload structure:
```json
{
  "event": "order.completed",
  "id": "evt_abc123",
  "created_at": "2024-01-15T10:30:00Z",
  "data": { }
}
```

## Performance Standards

- P50 latency < 100ms for read endpoints
- P99 latency < 500ms for read endpoints
- P99 latency < 2000ms for write endpoints
- Timeout all outbound calls at 5 seconds
- Cache frequently read, rarely changed data (TTL: 5–60 minutes)
- Use database indexes for all query fields

## Deprecation Process

1. Announce deprecation in `#eng-announcements` Slack
2. Add `Deprecation` header with sunset date
3. Email all active consumers with migration guide
4. Maintain deprecated version for minimum 6 months
5. Return `410 Gone` after sunset date
