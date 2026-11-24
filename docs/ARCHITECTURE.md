# DocuFlow — System Architecture

## Overview

DocuFlow is a multi-tenant SaaS platform for intelligent document processing. Documents are uploaded, processed asynchronously by AI workers, and reviewed by human operators through a document review workspace.

## Component Diagram

```
Browser (React SPA)
       │
       │ HTTPS + Bearer token
       ▼
FastAPI Application (port 8000)
       │                    │
       │                    │ Dispatch jobs
       ▼                    ▼
PostgreSQL (RLS)      Celery Worker
       │                    │
       │                    │ Download/upload
       ▼                    ▼
  (source of          MinIO / S3 Storage
   truth for all           │
   tenant data)            │ AI extraction
                           ▼
                   Anthropic Claude API
```

## Technology Stack

| Layer | Technology |
|---|---|
| Frontend | React 18 + TypeScript + Vite + TanStack Query |
| Backend | FastAPI + Python 3.11 |
| Database | PostgreSQL 16 with Row-Level Security |
| Cache/Queue | Redis 7 |
| Background Jobs | Celery |
| File Storage | MinIO (dev) / AWS S3 (prod) |
| AI Provider | Anthropic Claude (via provider abstraction) |
| Auth | JWT (access + refresh tokens) |

## Multi-Tenancy Model

Every tenant is an **Organization**. Each tenant-scoped database table has:
- An `organization_id` column (FK to `organizations`)
- Row-Level Security enabled + forced
- An RLS policy that checks `app.current_organization_id` session variable

The application sets this variable on every session via `set_config('app.current_organization_id', ...)` before executing any tenant-scoped query.

This provides **defense in depth** — even if application-level filtering is bypassed, the database will not return another tenant's rows.

## Authentication Flow

```
1. POST /api/v1/auth/login
   → access_token (JWT, 15min) in response body
   → refresh_token (JWT, 7 days) in httpOnly cookie (path=/api/v1/auth)

2. Frontend stores access_token in memory (Zustand store)
   → Injected as Authorization: Bearer <token> on every API request

3. On 401 response:
   → Axios interceptor POSTs to /api/v1/auth/refresh
   → Cookie sent automatically (withCredentials: true)
   → New access_token returned, stored in memory
   → Retry original request

4. On refresh failure:
   → User redirected to /login
```

## Document Processing Pipeline

```
Upload                                    Review
  │                                          ▲
  ▼                                          │
Validate magic bytes + size             Extraction stored
  │                                     status=review_pending
  ▼                                          ▲
Store to S3 (UUID key)                       │
  │                                     AI extracts fields
  ▼                                     + confidence scores
Create Document record                       ▲
  │                                          │
  ▼                                     Classify doc type
Dispatch Celery task                         ▲
  │                                          │
  ▼                                     Extract text (PDF/OCR)
status=queued                                ▲
                                             │
                                      Worker downloads file
```

## API Structure

All API routes are under `/api/v1/`.

| Resource | Base Path |
|---|---|
| Auth | `/api/v1/auth/` |
| Organizations | `/api/v1/organizations/` |
| Documents | `/api/v1/organizations/{org_id}/documents/` |
| Extractions | `/api/v1/organizations/{org_id}/extractions/` |
| Analytics | `/api/v1/organizations/{org_id}/analytics/` |

All tenant resources are scoped under `organizations/{org_id}` to enforce ownership at the URL level.

## Code Structure

```
backend/
  app/
    api/v1/endpoints/   # HTTP route handlers (thin layer)
    services/           # Business logic
    repositories/       # Database access
    models/             # SQLAlchemy ORM models
    schemas/            # Pydantic request/response schemas
    core/               # Config, DB session, security, dependencies
    workers/            # Celery background tasks
    utils/              # File validation, helpers

frontend/
  src/
    api/        # Axios API client functions
    pages/      # Route-level page components
    components/ # Reusable UI components
    stores/     # Zustand client state
    lib/        # Utilities (cn, formatters)
    types/      # TypeScript type definitions
```
