# syntax=docker/dockerfile:1

# Build stage: install dependencies for the chat analysis agent using uv on Python 3.13
FROM ghcr.io/astral-sh/uv:python3.13-bookworm AS builder

WORKDIR /app

# Copy workspace metadata and project configuration for dependency resolution
COPY pyproject.toml uv.lock ./
COPY agents/chat-analysis-agent/pyproject.toml agents/chat-analysis-agent/pyproject.toml
COPY packages/common/pyproject.toml packages/common/pyproject.toml

# Copy source trees required for editable installs before syncing dependencies
COPY packages/common packages/common
COPY agents/chat-analysis-agent agents/chat-analysis-agent

# Resolve dependencies and create a virtual environment tailored to the chat analysis agent package
RUN uv sync --frozen --no-dev --package chat-analysis-agent

# Runtime stage based on slim Python image
FROM python:3.13-slim AS runtime

ENV APP_HOME=/app \
    PATH="/app/.venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1

WORKDIR ${APP_HOME}

# Copy the prepared virtual environment and application sources from builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/agents/chat-analysis-agent /app/agents/chat-analysis-agent
COPY --from=builder /app/packages/common /app/packages/common
COPY --from=builder /app/pyproject.toml /app/pyproject.toml
COPY --from=builder /app/uv.lock /app/uv.lock

# .env file will be mounted as volume in docker-compose
EXPOSE 10000 10001 10002 10003
