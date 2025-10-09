# syntax=docker/dockerfile:1

# Build stage: install dependencies for the VOC agent using uv on Python 3.12
FROM ghcr.io/astral-sh/uv:python3.12-bookworm AS builder

WORKDIR /app

# Copy workspace metadata and project configuration for dependency resolution
COPY pyproject.toml uv.lock ./
COPY agents/voc-agent/pyproject.toml agents/voc-agent/pyproject.toml
COPY packages/common/pyproject.toml packages/common/pyproject.toml

# Copy source trees required for editable installs before syncing dependencies
COPY packages/common packages/common
COPY agents/voc-agent agents/voc-agent

# Resolve dependencies and create a virtual environment tailored to the voc-agent package
RUN uv sync --frozen --no-dev --package voc-agent

# Runtime stage based on slim Python image
FROM python:3.12-slim AS runtime

ENV APP_HOME=/app \
    PATH="/app/.venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1

WORKDIR ${APP_HOME}

# Copy the prepared virtual environment and application sources from builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/agents/voc-agent /app/agents/voc-agent
COPY --from=builder /app/packages/common /app/packages/common
COPY --from=builder /app/pyproject.toml /app/pyproject.toml
COPY --from=builder /app/uv.lock /app/uv.lock

EXPOSE 10000 10001

# Default to running the orchestration service; override in compose for other entrypoints
CMD ["python", "-m", "voc_agent.orchestrator.__main__"]
