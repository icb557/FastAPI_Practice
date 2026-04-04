# ── Development ────────────────────────────────────────────────────────────────
FROM dhi.io/uv:0-debian12-dev AS dev

WORKDIR /app

# Place the venv outside /app so the bind-mount (.:/app) never overwrites it.
ENV UV_PROJECT_ENVIRONMENT=/venv

# Only copy dependency files so Docker can cache this layer independently
# from source-code changes. The full source is mounted as a volume at runtime.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen

ENV PATH="/venv/bin:$PATH"

EXPOSE 8000

# Command is defined in docker-compose.yml so it is easy to change without
# rebuilding the image.

# ── Builder ────────────────────────────────────────────────────────────────────
# FROM dhi.io/uv:0-debian12-dev AS builder
FROM dhi.io/python:3.12-debian12-dev AS builder
COPY --from=dhi.io/uv:0-debian12-dev /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

WORKDIR /app

# Install dependencies first (better caching)
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

# Copy the rest of the app
COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# ── Production ────────────────────────────────────────────────────────────────
# Uses the hardened, non-root runtime image
FROM dhi.io/python:3.12-debian12 AS prod

WORKDIR /app

# Copy only the virtual environment from the builder
COPY --from=builder /app/.venv /app/.venv

ENV PATH="/app/.venv/bin:$PATH"
# Ensure Python logs are immediately printed to the Docker stream
ENV PYTHONUNBUFFERED=1

COPY . .

EXPOSE 8000

ENTRYPOINT [ "python", "scripts/start.py" ]

# Start FastAPI using the optimized production command
CMD ["python", "-m", "fastapi", "run", "--port", "8000"]
# CMD ["ls", "-la", "/app/.venv/bin/fastapi"]