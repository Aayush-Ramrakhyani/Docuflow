FROM python:3.11-slim

# Faster, cleaner Python in containers:
#  - no .pyc files written to disk
#  - stdout/stderr unbuffered so logs appear immediately
#  - pip doesn't keep a wheel cache or check for upgrades
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install system deps for PyMuPDF and python-magic
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagic1 \
    libmupdf-dev \
    && rm -rf /var/lib/apt/lists/*

# INSTALL_DEV=true (default) includes test/lint deps for the compose dev setup.
# Production builds should pass --build-arg INSTALL_DEV=false for a leaner image.
ARG INSTALL_DEV=true

# Dependency layer is cached unless pyproject.toml changes — keeps rebuilds fast.
COPY pyproject.toml .
RUN if [ "$INSTALL_DEV" = "true" ]; then \
        pip install -e ".[dev]"; \
    else \
        pip install -e "."; \
    fi

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
