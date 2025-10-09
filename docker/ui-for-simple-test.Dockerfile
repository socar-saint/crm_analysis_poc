# syntax=docker/dockerfile:1

# Build stage: install dependencies for the UI using uv on Python 3.12
FROM ghcr.io/astral-sh/uv:python3.12-bookworm AS builder

WORKDIR /app

# Copy workspace metadata and project configuration for dependency resolution
COPY pyproject.toml uv.lock ./
COPY packages/ui-for-simple-test/pyproject.toml packages/ui-for-simple-test/pyproject.toml
COPY packages/common/pyproject.toml packages/common/pyproject.toml

# Copy source trees required for editable installs before syncing dependencies
COPY packages/common packages/common
COPY packages/ui-for-simple-test packages/ui-for-simple-test

# Resolve dependencies and create a virtual environment tailored to the ui-for-simple-test package
RUN uv sync --frozen --no-dev --package ui-for-simple-test

# Runtime stage based on slim Python image with Node.js for Reflex frontend
FROM python:3.12-slim AS runtime

# Install Node.js and required system packages for Reflex frontend
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl ca-certificates unzip && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

ENV APP_HOME=/app \
    PATH="/app/.venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1

WORKDIR ${APP_HOME}

# Copy the prepared virtual environment and application sources from builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/packages/ui-for-simple-test /app/packages/ui-for-simple-test
COPY --from=builder /app/packages/common /app/packages/common
COPY --from=builder /app/pyproject.toml /app/pyproject.toml
COPY --from=builder /app/uv.lock /app/uv.lock

WORKDIR /app/packages/ui-for-simple-test

EXPOSE 3000 8000

# Run reflex (will automatically initialize and build frontend on first run)
CMD ["reflex", "run", "--env", "prod", "--loglevel", "info"]
