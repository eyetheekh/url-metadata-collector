########################################################
# build
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && update-ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# install uv
COPY --from=ghcr.io/astral-sh/uv:0.10.0 /uv /uvx /bin/

WORKDIR /build

COPY pyproject.toml uv.lock ./

# no symlink venv
RUN python -m venv /opt/venv --copies
RUN /opt/venv/bin/python -m pip install -U pip

# install deps
RUN uv export --no-dev > requirements.txt && \
    /opt/venv/bin/python -m pip install --no-cache-dir -r requirements.txt && \
    rm -f requirements.txt /bin/uv /bin/uvx


########################################################
# runtime
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && update-ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY app/ ./app/

RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

ENV WORKERS=4
ENV SERVER_TIMEOUT=300

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD gunicorn app.main:app \
    -k uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --workers ${WORKERS} \
    --timeout ${SERVER_TIMEOUT}
