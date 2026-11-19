# syntax=docker/dockerfile:1.7
FROM python:3.14-slim-bookworm@sha256:3fe1a0b6c2d6b2ebb572906cdabeca75aeb558c0c17db5ffefbcf8094871c32b AS base
COPY --from=ghcr.io/astral-sh/uv:0.13.6@sha256:af22a52f5eafef3d78e551599d405c02df61919d18028f0cea8eda93bc9986d0 /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /src

RUN groupadd --system nonroot \
    && useradd --system --gid nonroot --home-dir /src nonroot \
    && mkdir -p /opt/venv \
    && chown -R nonroot:nonroot /src /opt/venv

# -----------------------------------------------------------------------------
# deps: install locked runtime dependencies only — cached separately from app code
# -----------------------------------------------------------------------------
FROM base AS deps

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev --no-editable

# -----------------------------------------------------------------------------
# source: project files the dev and prod installs both build from
# -----------------------------------------------------------------------------
FROM deps AS source

COPY pyproject.toml uv.lock README.md alembic.ini ./
COPY ./app ./app
COPY ./migrations ./migrations

# -----------------------------------------------------------------------------
# dev: editable install with the dev group. Compose bind-mounts ./backend over
# /src, and the editable install points there, so uvicorn --reload sees changes.
# The dev group is installed before the code is copied, so a code change only
# re-runs the editable install of the project itself.
# -----------------------------------------------------------------------------
FROM deps AS dev

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project

COPY --from=source /src /src
COPY ./devtools ./devtools

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked

# -----------------------------------------------------------------------------
# builder: install the project itself into /opt/venv
# -----------------------------------------------------------------------------
FROM source AS builder

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-editable

# -----------------------------------------------------------------------------
# final: minimal production image
# -----------------------------------------------------------------------------
FROM base AS final

COPY --from=builder --chown=nonroot:nonroot /opt/venv /opt/venv
COPY --from=builder --chown=nonroot:nonroot /src/app ./app
COPY --from=builder --chown=nonroot:nonroot /src/migrations ./migrations
COPY --from=builder --chown=nonroot:nonroot /src/alembic.ini ./alembic.ini

USER nonroot
