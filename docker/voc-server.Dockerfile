# syntax=docker/dockerfile:1

# Build stage: resolve dependencies with uv using Python 3.12
FROM ghcr.io/astral-sh/uv:python3.12-bookworm AS builder

WORKDIR /app

# Copy workspace metadata and project configuration first for better caching
COPY pyproject.toml uv.lock ./
COPY mcp-servers/voc-server/pyproject.toml mcp-servers/voc-server/pyproject.toml

# Copy the project sources (Hatch requires packages to be present to build editables)
COPY mcp-servers/voc-server mcp-servers/voc-server

# Install locked dependencies and the project itself (creates `.venv` under /app)
RUN uv sync --frozen --no-dev --package voc-server

# Runtime stage: slim Python with the pre-built virtualenv
FROM python:3.12-slim AS runtime

ENV APP_HOME=/app \
    PATH="/app/.venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1

WORKDIR ${APP_HOME}

# System dependencies required at runtime
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy application virtual environment and sources from the builder stage
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/mcp-servers/voc-server /app

EXPOSE 9000

CMD ["python", "-m", "voc_server.server"]
