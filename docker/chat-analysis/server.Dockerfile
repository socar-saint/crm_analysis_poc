# syntax=docker/dockerfile:1

# Build stage: install dependencies for the chat analysis server using uv on Python 3.13
FROM ghcr.io/astral-sh/uv:python3.13-bookworm AS builder

WORKDIR /app

# Copy workspace metadata and project configuration for dependency resolution
COPY pyproject.toml uv.lock ./
COPY mcp-servers/chat-analysis-mcp-server/pyproject.toml mcp-servers/chat-analysis-mcp-server/pyproject.toml
COPY packages/common/pyproject.toml packages/common/pyproject.toml

# Copy source trees required for editable installs before syncing dependencies
COPY packages/common packages/common
COPY mcp-servers/chat-analysis-mcp-server mcp-servers/chat-analysis-mcp-server

# Resolve dependencies and create a virtual environment tailored to the chat analysis server package
RUN uv sync --frozen --no-dev --package chat-analysis-mcp-server

# Runtime stage based on slim Python image
FROM python:3.13-slim AS runtime

ENV APP_HOME=/app \
    PATH="/app/.venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1

WORKDIR ${APP_HOME}

# Copy the prepared virtual environment and application sources from builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/mcp-servers/chat-analysis-mcp-server /app/mcp-servers/chat-analysis-mcp-server
COPY --from=builder /app/packages/common /app/packages/common
COPY --from=builder /app/pyproject.toml /app/pyproject.toml
COPY --from=builder /app/uv.lock /app/uv.lock

# .env file will be mounted as volume in docker-compose

EXPOSE 50000
