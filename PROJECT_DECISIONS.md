# DocuFlow — Project Decisions Log

This file is the permanent technical decision log for DocuFlow. Every significant architectural, security, or product decision must be recorded here. Read this before making architectural changes.

---

## System Architecture

### ADR-001: Modular Monolith with Separated Frontend/Backend

- **Decision:** Build a modular monolith backend (FastAPI) with a separate React frontend. No microservices at this stage.
- **Context:** DocuFlow requires fast iteration, tenant isolation, and complex document workflows. Microservices would add operational overhead without meaningful benefit for a v1 product.
- **Reasoning:** Modular monolith allows refactoring into services later without premature complexity. Single deployment unit simplifies operations.
- **Alternatives:** Microservices (rejected — premature), serverless functions (rejected — stateful document processing unsuitable), full-stack framework like Next.js (rejected — Python backend required for AI/ML).
- **Trade-offs:** Harder horizontal scaling of specific subsystems; easier local development and debugging.
- **Implementation:** `backend/` (FastAPI), `frontend/` (React/Vite), `docker-compose.yml` orchestration.
- **Status:** Accepted
- **Date:** 2026-11-24

---

### ADR-002: Technology Stack

- **Decision:** FastAPI + PostgreSQL + Redis + Celery backend; React + TypeScript + Vite + TanStack frontend.
- **Context:** Need a typed, fast Python backend with async support, background job processing, and a modern React frontend.
- **Reasoning:**
  - FastAPI: async-native, automatic OpenAPI docs, Pydantic integration, strong typing
  - PostgreSQL: JSONB for extraction data, full RLS support, battle-tested
  - Redis: job queue backing, session cache
  - Celery: mature Python background job library
  - React + Vite: fast builds, large ecosystem
  - TanStack Query: excellent server-state management
  - TanStack Router: type-safe routing
  - Zustand: lightweight client-state
- **Alternatives:** Django REST Framework (slower, less async), Flask (too minimal), Django (too opinionated); Next.js (rejected per ADR-001); Remix (less ecosystem maturity).
- **Status:** Accepted
- **Date:** 2026-11-24

---

## Backend Engineering

### ADR-003: Repository Pattern with Services Layer

- **Decision:** Use Repository → Service → Router layers. Repositories handle DB access; services implement business logic; routers handle HTTP concerns.
- **Context:** Keeping business logic in route handlers creates untestable, mixed-concern code.
- **Reasoning:** Each layer is independently testable. Services can be called from both HTTP handlers and background workers. Repositories abstract SQLAlchemy specifics.
- **Alternatives:** Active Record pattern (couples business logic to models), fat controllers (rejected — untestable).
- **Implementation:** `app/repositories/`, `app/services/`, `app/api/v1/endpoints/`
- **Status:** Accepted
- **Date:** 2026-11-24

---

### ADR-004: Pydantic v2 for Validation

- **Decision:** Use Pydantic v2 for all input/output validation and configuration.
- **Context:** All FastAPI request/response schemas and application settings require validation.
- **Reasoning:** Pydantic v2 is significantly faster than v1; native integration with FastAPI; model_config replaces Config inner class.
- **Status:** Accepted
- **Date:** 2026-11-24

---

## Database and Data Modelling

### ADR-005: Multi-Tenancy via Organization-Scoped RLS

- **Decision:** Use PostgreSQL Row-Level Security on all tenant-owned tables. Every tenant-owned row includes an `organization_id` column.
- **Context:** DocuFlow is a multi-tenant SaaS. Users must never access another organization's data.
- **Reasoning:** RLS enforces isolation at the database level, preventing bugs in application-level filtering from leaking data. Defense in depth.
- **Alternatives:** Schema-per-tenant (rejected — too complex to migrate), database-per-tenant (rejected — operationally expensive), application-only filtering (rejected — insufficient isolation).
- **Implementation:** All tables with tenant data have RLS enabled. Policies use `current_setting('app.current_organization_id')` to scope reads/writes.
- **Consequences:** Application must set `app.current_organization_id` on every DB session. Migrations must run as a privileged role that bypasses RLS.
- **Status:** Accepted
- **Date:** 2026-11-24

---

### ADR-006: JSONB for Extraction Field Data

- **Decision:** Store extraction field results as JSONB in PostgreSQL rather than a wide relational table.
- **Context:** Different document schemas produce different fields. Extraction results vary by document type (invoice, contract, receipt, etc.).
- **Reasoning:** JSONB allows flexible, schema-less extraction storage while remaining queryable. No schema migration needed to support new document types.
- **Alternatives:** EAV (entity-attribute-value) tables (rejected — complex queries, poor performance), fixed columns (rejected — too rigid for varied document types), MongoDB (rejected — keeping single DB).
- **Trade-offs:** Less strict schema enforcement at DB level; application-level validation required.
- **Implementation:** `extractions.extracted_data JSONB NOT NULL DEFAULT '{}'::jsonb`
- **Status:** Accepted
- **Date:** 2026-11-24

---

### ADR-007: UUID Primary Keys

- **Decision:** Use UUID v4 for all primary keys instead of auto-incrementing integers.
- **Context:** Public APIs and URL paths would expose sequential integer IDs, making enumeration attacks trivial.
- **Reasoning:** UUIDs prevent IDOR enumeration even without RLS. Work with distributed systems. Standard for SaaS APIs.
- **Trade-offs:** Larger index size; slightly slower joins; not human-readable.
- **Status:** Accepted
- **Date:** 2026-11-24

---

## Authentication and Authorization

### ADR-008: JWT Access + Refresh Tokens (No Session Cookies for API)

- **Decision:** Use short-lived JWT access tokens (15 min) and long-lived refresh tokens (7 days) stored in httpOnly cookies. The access token is passed in the Authorization header.
- **Context:** DocuFlow has a REST API consumed by a React SPA.
- **Reasoning:** Short-lived access tokens limit the blast radius of token leakage. Refresh tokens in httpOnly cookies are protected from JS XSS. This avoids CSRF risks from cookie-based session auth while protecting refresh tokens.
- **Alternatives:** Session-only cookies (simpler but CSRF-prone), long-lived access tokens (rejected — no revocation path), localStorage tokens (rejected — XSS exposure).
- **Implementation:** `app/core/security.py`, `/api/v1/auth/` endpoints
- **Consequences:** Frontend must handle 401 responses by attempting token refresh before re-authenticating.
- **Status:** Accepted
- **Date:** 2026-11-24

---

### ADR-009: Argon2id Password Hashing

- **Decision:** Use Argon2id for password hashing (via `argon2-cffi`).
- **Context:** Standard password storage for user accounts.
- **Reasoning:** Argon2id is the OWASP-recommended algorithm, winner of the Password Hashing Competition. Memory-hard, resistant to GPU and ASIC attacks. Superior to bcrypt and PBKDF2.
- **Status:** Accepted
- **Date:** 2026-11-24

---

### ADR-010: Organization-Level RBAC

- **Decision:** Three roles per organization: `owner`, `admin`, `member`. Enforced at the service layer and RLS policies.
- **Context:** Organizations need role differentiation for managing members, API keys, webhooks, and billing.
- **Roles:**
  - `owner`: Full access; can delete organization; cannot be removed by others
  - `admin`: Can manage members, API keys, webhooks; cannot delete organization
  - `member`: Can upload and review documents; cannot manage team
- **Status:** Accepted
- **Date:** 2026-11-24

---

## Security

### ADR-011: File Upload Security Architecture

- **Decision:** Validate file magic bytes (not extension), enforce size limits, generate server-side safe filenames, store in private S3 with signed URLs, run Pillow/PyMuPDF content validation before processing.
- **Context:** DocuFlow processes uploaded documents from untrusted users.
- **Reasoning:** Client-supplied filenames and MIME types are untrusted. Magic byte validation ensures the file is actually the claimed type. Server-side filenames prevent path traversal.
- **Implementation:** `app/services/storage.py`, `app/utils/file_validation.py`
- **Consequences:** Uploaded files are always stored with UUIDs as filenames. Original filename stored in metadata only.
- **Status:** Accepted
- **Date:** 2026-11-24

---

### ADR-012: Signed Short-Lived S3 URLs for Document Access

- **Decision:** Never expose permanent public URLs for documents. All document access uses signed URLs with 1-hour expiration, generated after authorization checks.
- **Context:** Documents are sensitive business data.
- **Reasoning:** Permanent public URLs would allow anyone with the URL to access documents indefinitely. Signed URLs expire and are generated only after the backend confirms authorization.
- **Status:** Accepted
- **Date:** 2026-11-24

---

## API Design

### ADR-013: Versioned REST API under /api/v1/

- **Decision:** All API routes under `/api/v1/`. Version prefix allows future breaking changes without disrupting existing clients.
- **Context:** DocuFlow will expose APIs to both the frontend and external integrations.
- **Status:** Accepted
- **Date:** 2026-11-24

---

## Document Processing and AI Integration

### ADR-014: Asynchronous Document Processing via Celery

- **Decision:** All document processing (OCR, AI extraction, validation) runs in Celery background workers, not in API request handlers.
- **Context:** Document processing can take 5–60 seconds per document. Blocking API requests would cause timeouts.
- **Reasoning:** Async workers allow immediate API response ("processing started"), progress tracking via job status polling, retry on failure, and horizontal scaling.
- **Implementation:** `app/workers/document_processor.py`, status tracked in `processing_jobs` table.
- **Status:** Accepted
- **Date:** 2026-11-24

---

### ADR-015: AI Provider Abstraction Layer

- **Decision:** All AI calls go through an abstract `AIProvider` interface. The default implementation uses Anthropic Claude. Additional providers can be added without changing calling code.
- **Context:** AI provider landscape is evolving. DocuFlow should not be hard-wired to one provider.
- **Reasoning:** Provider abstraction allows swapping models, A/B testing, and fallback providers without touching document processing logic.
- **Implementation:** `app/services/ai/base.py`, `app/services/ai/anthropic_provider.py`
- **Status:** Accepted
- **Date:** 2026-11-24

---

### ADR-016: Prompt Injection Mitigation

- **Decision:** Document content sent to AI is wrapped in XML delimiters and the AI is instructed to treat document content as data, not instructions. AI output is validated against explicit Pydantic schemas.
- **Context:** Uploaded documents may contain adversarial text designed to hijack AI extraction.
- **Reasoning:** Structural separation of instructions from document content, combined with schema validation of responses, reduces prompt injection risk.
- **Status:** Accepted
- **Date:** 2026-11-24

---

## UI/UX and Design System

### ADR-017: Arctic Precision Design Theme

- **Decision:** Use the "Arctic Precision" visual direction: light content area, dark slate sidebar (#0F172A), amber accent (#F59E0B), Inter + JetBrains Mono typography.
- **Context:** Must avoid generic AI SaaS aesthetics (purple-blue gradients, white cards on grey, glassmorphism).
- **Reasoning:** Amber accent is rare in enterprise software, immediately distinctive. Dark sidebar / light content is a proven enterprise pattern. Communicates trust and precision. Fully evaluated against two alternative directions. See `docs/DESIGN_RESEARCH.md`.
- **Implementation:** `frontend/src/lib/design-tokens.ts`, `tailwind.config.ts`, `frontend/src/index.css`
- **Status:** Accepted
- **Date:** 2026-11-24

---

### ADR-018: shadcn/ui as Component Foundation (Heavily Customized)

- **Decision:** Use shadcn/ui as the component base, overriding all default styles to match the Arctic Precision design system.
- **Context:** Building every UI component from scratch is impractical; shadcn/ui provides accessible, composable primitives.
- **Reasoning:** shadcn/ui copies components into the project (not a black-box dependency), allowing full customization. Accessible by default. Integrates with Radix UI primitives.
- **Trade-offs:** Requires CSS variable customization and Tailwind overrides. Components will not look like default shadcn/ui.
- **Status:** Accepted
- **Date:** 2026-11-24

---

## Infrastructure and Deployment

### ADR-019: Docker Compose for Local Development

- **Decision:** Docker Compose for local development with services: api, worker, frontend (dev server), postgres, redis, minio (S3-compatible).
- **Context:** Developers need a consistent local environment.
- **Status:** Accepted
- **Date:** 2026-11-24

---

## Third-Party Dependencies

### ADR-020: Key Dependency Selections

| Purpose | Library | Rationale |
|---|---|---|
| Password hashing | argon2-cffi | OWASP recommended, Argon2id |
| JWT | python-jose | Widely used, supports RS256 |
| File validation | python-magic | Magic byte inspection |
| PDF processing | PyMuPDF (fitz) | Fast, reliable, extracts text+images |
| S3 client | boto3 | Standard AWS SDK |
| Background jobs | Celery + Redis | Mature Python async job library |
| Rate limiting | slowapi | FastAPI-native, Redis-backed |
| AI provider | anthropic (official SDK) | Claude 3.5 Sonnet for extraction |
| DB migrations | Alembic | SQLAlchemy-native |
| Frontend routing | TanStack Router v1 | Type-safe routing |
| Server state | TanStack Query v5 | Best-in-class data fetching |
| Form validation | Zod + React Hook Form | Type-safe, schema-driven |
| PDF viewer | react-pdf | Renders PDF.js in React |

- **Status:** Accepted
- **Date:** 2026-11-24

---

## Superseded Decisions

_None yet._
