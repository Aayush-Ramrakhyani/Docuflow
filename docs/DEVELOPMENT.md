# DocuFlow — Development Guide

## Prerequisites

- Docker + Docker Compose
- Node.js 20+
- Python 3.11+
- An Anthropic API key (for AI extraction)

## Quick Start

### 1. Clone and configure

```bash
cp .env.example .env
# Edit .env — set ANTHROPIC_API_KEY and SECRET_KEY at minimum
```

Generate a secure SECRET_KEY:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 2. Start infrastructure

```bash
docker compose up postgres redis minio minio-setup -d
```

### 3. Run database migrations

```bash
cd backend
pip install -e ".[dev]"
alembic upgrade head
```

### 4. Start the backend

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

### 5. Start the Celery worker

In a separate terminal:
```bash
cd backend
celery -A app.core.celery_app worker --loglevel=info
```

### 6. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

The app is available at http://localhost:5173.

API docs (dev only) at http://localhost:8000/docs.

## Running Tests

```bash
cd backend
pytest -v

# With coverage
pytest --cov=app --cov-report=html
```

## Running Linting and Type Checks

```bash
# Backend
cd backend
ruff check .
mypy app/

# Frontend
cd frontend
npm run type-check
npm run lint
```

## Database Migrations

```bash
# Create a new migration
cd backend
alembic revision --autogenerate -m "describe the change"

# Apply migrations
alembic upgrade head

# Downgrade one revision
alembic downgrade -1
```

## Environment Variables

All configuration is documented in `.env.example`. Critical variables:

| Variable | Description |
|---|---|
| `SECRET_KEY` | JWT signing key — must be secure random |
| `DATABASE_URL` | PostgreSQL connection string |
| `ANTHROPIC_API_KEY` | Anthropic API key for AI extraction |
| `ENVIRONMENT` | `development`, `staging`, or `production` |

## Project Structure

See `docs/ARCHITECTURE.md` for a full overview.

## Code Style

- Backend: `ruff` for linting and formatting, `mypy --strict` for types
- Frontend: TypeScript strict mode, ESLint
- Commits: conventional commits (`feat:`, `fix:`, `chore:`, `docs:`)
