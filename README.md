# DocuFlow

**Intelligent document processing platform.** Upload documents, extract structured data with AI, review and approve results through a precision-built workspace.

---

## What DocuFlow Does

1. **Upload** — Drop a PDF, invoice, contract, or image
2. **Process** — AI automatically extracts structured fields with confidence scores
3. **Review** — Side-by-side document viewer + extraction panel; correct low-confidence fields
4. **Approve** — Human-in-the-loop approval before data is considered final
5. **Export** — Access approved extractions via API or webhooks

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18 + TypeScript + Vite + TanStack Query |
| Backend | FastAPI + Python 3.11 |
| Database | PostgreSQL 16 (with RLS for multi-tenancy) |
| Background Jobs | Celery + Redis |
| File Storage | MinIO (dev) / AWS S3 (prod) |
| AI Extraction | Anthropic Claude |
| Auth | JWT (access + refresh tokens, Argon2id hashing) |

## Design

**Arctic Precision** — dark slate sidebar (#0F172A) + light content area + amber accent (#F59E0B). Precision, trust, and professionalism over generic AI aesthetics.

See `docs/DESIGN_SYSTEM.md` and `docs/DESIGN_RESEARCH.md`.

---

## Quick Start

### Prerequisites
- Docker + Docker Compose
- Node.js 20+
- Python 3.11+
- Anthropic API key

### 1. Configure

```bash
cp .env.example .env
# Set SECRET_KEY and ANTHROPIC_API_KEY
```

### 2. Start infrastructure

```bash
docker compose up postgres redis minio minio-setup -d
```

### 3. Run migrations

```bash
cd backend
pip install -e ".[dev]"
alembic upgrade head
```

### 4. Start services

Terminal 1 (API):
```bash
cd backend && uvicorn app.main:app --reload
```

Terminal 2 (Worker):
```bash
cd backend && celery -A app.core.celery_app worker --loglevel=info
```

Terminal 3 (Frontend):
```bash
cd frontend && npm install && npm run dev
```

App: **http://localhost:5173**  
API Docs: **http://localhost:8000/docs**

---

## Project Structure

```
docuflow/
├── backend/              # FastAPI application
│   ├── app/
│   │   ├── api/v1/       # HTTP routes
│   │   ├── services/     # Business logic + AI
│   │   ├── repositories/ # Data access
│   │   ├── models/       # SQLAlchemy ORM
│   │   ├── schemas/      # Pydantic schemas
│   │   ├── workers/      # Celery tasks
│   │   └── core/         # Config, DB, security
│   ├── migrations/       # Alembic
│   └── tests/
├── frontend/             # React application
│   └── src/
│       ├── pages/        # Route-level pages
│       ├── components/   # Reusable UI components
│       ├── api/          # API client functions
│       └── stores/       # Zustand state
├── docs/
│   ├── ARCHITECTURE.md
│   ├── DESIGN_SYSTEM.md
│   ├── DESIGN_RESEARCH.md
│   ├── DEVELOPMENT.md
│   ├── SECURITY_CHECKLIST.md
│   └── API.md
├── PROJECT_DECISIONS.md  # Architectural decision log
└── SECURITY.md
```

---

## Security

DocuFlow is built with security-first principles:

- **Multi-tenant isolation** via PostgreSQL RLS
- **Private file storage** — all documents in private S3, accessed via short-lived signed URLs
- **Argon2id** password hashing
- **JWT** with short-lived access tokens + httpOnly refresh cookies
- **Input validation** at every boundary
- **Audit logging** of all sensitive actions
- **Prompt injection mitigation** for AI document processing

See `docs/SECURITY_CHECKLIST.md` for the full 19-check evaluation.

---

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Development Guide](docs/DEVELOPMENT.md)
- [Design System](docs/DESIGN_SYSTEM.md)
- [Design Research](docs/DESIGN_RESEARCH.md)
- [Security Checklist](docs/SECURITY_CHECKLIST.md)
- [Project Decisions](PROJECT_DECISIONS.md)
- [Security Policy](SECURITY.md)

---

## License

MIT License — see LICENSE file.

> **Note:** This project was built for practice and learning purposes.
> If you'd like to use it, adapt it, or collaborate, feel free to reach out:
> **aayushr7777@gmail.com**
