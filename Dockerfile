FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && rm -rf /var/lib/apt/lists/*

# Install deps as a separate layer — only rebuilds when pyproject.toml changes
COPY pyproject.toml .
RUN pip install --no-cache-dir \
    "fastapi>=0.111.0" \
    "uvicorn[standard]>=0.29.0" \
    "sqlalchemy[asyncio]>=2.0.0" \
    asyncpg \
    "alembic>=1.13.0" \
    "celery[redis]>=5.3.0" \
    "pydantic-settings>=2.2.0" \
    "httpx>=0.27.0" \
    "cryptography>=42.0.0" \
    "python-jose[cryptography]>=3.3.0" \
    "python-multipart>=0.0.9" \
    pytest \
    "pytest-asyncio>=0.23.0" \
    "respx>=0.21.0"

COPY kistbook/ kistbook/
COPY alembic.ini .

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
