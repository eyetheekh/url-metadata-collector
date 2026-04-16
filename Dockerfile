########################################################
# builder
FROM ubuntu:26.04 AS builder

ENV DEBIAN_FRONTEND=noninteractive
ENV UV_SYSTEM_PYTHON=0

# minimal deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# install uv
RUN curl -Ls https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app

# copy dependency files
COPY pyproject.toml uv.lock ./

# create Python 3.11 environment via uv
RUN uv venv /opt/venv --python 3.11 \
    && . /opt/venv/bin/activate \
    && uv sync --frozen --no-dev

# copy source
COPY . .

########################################################
# runtime
FROM ubuntu:26.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

# only required runtime libs (no python3 from apt!)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# copy venv (includes Python 3.11 runtime)
COPY --from=builder /opt/venv /opt/venv

# copy app
WORKDIR /app
COPY --from=builder /app /app

# non-root user
RUN useradd -m appuser
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]