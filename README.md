# Notetaker API

A simple note-taker REST API built with FastAPI, following the MVC architectural pattern, backed by PostgreSQL, and fully containerized with Docker.

## Quick Start

```bash
docker compose up --build -d
```

- API: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Project Structure (MVC)

```
app/
├── config.py        # Settings (pydantic-settings)
├── database.py      # SQLAlchemy engine + session dependency
├── main.py          # FastAPI app factory + lifespan
├── models/          # M — SQLAlchemy ORM models
│   └── note.py
├── schemas/         # V — Pydantic request/response schemas
│   └── note.py
├── services/        # C — Business logic / CRUD operations
│   └── note.py
└── routers/         # Route handlers (thin controllers)
    └── note.py
```

The MVC pattern maps as follows:

- **Models** = `models/` (database tables) + `schemas/` (API contract)
- **Views** = `routers/` (HTTP layer that receives requests and returns responses)
- **Controllers** = `services/` (business logic sitting between routes and the ORM)

## API Endpoints

| Method   | Path                      | Description                             |
| -------- | ------------------------- | --------------------------------------- |
| `GET`    | `/health`                 | Health check                            |
| `POST`   | `/api/v1/notes/`          | Create a note                           |
| `GET`    | `/api/v1/notes/`          | List notes (optional `?search=` query)  |
| `GET`    | `/api/v1/notes/{note_id}` | Get a single note                       |
| `PUT`    | `/api/v1/notes/{note_id}` | Update a note (partial updates allowed) |
| `DELETE` | `/api/v1/notes/{note_id}` | Delete a note                           |

## Tool-by-Tool Explanation

### 1. UV — Package & Project Manager

UV is a fast Python package and project manager written in Rust. It replaces `pip`, `pip-tools`, `venv`, and `pyenv` in a single binary.

| Command                 | Purpose                                                            |
| ----------------------- | ------------------------------------------------------------------ |
| `uv init`               | Scaffolds the project with `pyproject.toml` and `.python-version`  |
| `uv add <pkg>`          | Adds a dependency and updates the lockfile (`uv.lock`)             |
| `uv add --dev <pkg>`    | Adds a development-only dependency (ruff, mypy)                    |
| `uv sync --frozen`      | Installs from the lockfile for reproducible builds (used in Docker)|
| `uv run <cmd>`          | Runs a command inside the managed virtualenv                       |

All project metadata and dependencies live in `pyproject.toml`. The `uv.lock` file pins exact versions for reproducibility.

### 2. Uvicorn — ASGI Server

Uvicorn is a lightning-fast ASGI server that serves the FastAPI application. The `[standard]` extra installs performance extensions:

- **uvloop** — a faster drop-in replacement for asyncio's event loop
- **httptools** — a faster HTTP parser

The container startup command is:

```
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

`app.main:app` tells Uvicorn to import the `app` object from the `app/main.py` module.

### 3. Pydantic + pydantic-settings

#### Pydantic v2 (Schemas)

Pydantic handles all request/response validation. Every schema in `app/schemas/note.py` inherits from `BaseModel`:

- **`NoteCreate`** — validates incoming POST bodies (title, content, is_pinned)
- **`NoteUpdate`** — validates incoming PUT bodies (all fields optional for partial updates)
- **`NoteResponse`** — serializes ORM model instances to JSON. `from_attributes=True` enables direct SQLAlchemy object-to-dict conversion.
- **`NoteList`** — wraps a list of `NoteResponse` objects with a count

#### pydantic-settings (Configuration)

`app/config.py` defines a `Settings` class that reads environment variables and `.env` files into typed Python attributes:

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", ...)

    postgres_user: str = "notetaker"
    postgres_password: str = "notetaker"
    postgres_host: str = "db"
    postgres_port: int = 5432
    postgres_db: str = "notetaker"
```

The `@property` methods build the database URL dynamically from individual `POSTGRES_*` vars, so connection strings are never hardcoded. The app fails fast on startup if any required config is missing or invalid.

### 4. SQLAlchemy 2.0 (Async ORM)

SQLAlchemy was chosen as the ORM because it is the most mature Python ORM with first-class async support (via `sqlalchemy[asyncio]` + `asyncpg`).

Key components in `app/database.py`:

- **`create_async_engine`** — creates an async connection pool using `asyncpg` as the PostgreSQL driver
- **`async_sessionmaker`** — creates session factories bound to the engine (`expire_on_commit=False` prevents lazy-load issues after commit)
- **`get_db()`** — a FastAPI dependency that yields a session per request and auto-closes it
- **`Base`** — the declarative base class that all ORM models inherit from

The Note model in `app/models/note.py` uses SQLAlchemy 2.0's `Mapped` + `mapped_column` syntax for fully typed column declarations with UUID primary keys and server-side timestamp defaults.

### 5. Alembic — Database Migrations

Alembic manages database schema migrations. The `migrations/env.py` has been rewritten to use `async_engine_from_config` so it works with the async `asyncpg` driver.

Key details:

- `env.py` imports `Base.metadata` from `app.database` and all models, enabling autogenerate support
- `config.set_main_option("sqlalchemy.url", settings.database_url)` injects the URL from pydantic-settings at runtime (no hardcoded URL in `alembic.ini`)
- On container start, `alembic upgrade head` runs all pending migrations **before** Uvicorn starts

Common commands:

```bash
# Create a new migration
uv run alembic revision --autogenerate -m "description"

# Apply all migrations
uv run alembic upgrade head

# Rollback one migration
uv run alembic downgrade -1
```

### 6. Ruff — Linter & Formatter

Ruff is an extremely fast Python linter and formatter written in Rust. It replaces `flake8`, `isort`, `pyupgrade`, and `black` in a single tool.

Configuration in `pyproject.toml`:

```toml
[tool.ruff]
target-version = "py312"
line-length = 88

[tool.ruff.lint]
select = [
    "E",   # pycodestyle errors
    "F",   # pyflakes
    "W",   # pycodestyle warnings
    "I",   # isort (import sorting)
    "UP",  # pyupgrade (modernize syntax)
    "B",   # flake8-bugbear (common bugs)
    "SIM", # flake8-simplify (code simplification)
]

[tool.ruff.format]
quote-style = "double"
```

What each rule set does:

| Rule | Purpose |
| ---- | ------- |
| `E/W` | Standard PEP 8 style checks (indentation, whitespace, line length) |
| `F` | Detects unused imports, undefined names, and other logical errors |
| `I` | Sorts and groups imports consistently (replaces `isort`) |
| `UP` | Auto-upgrades syntax to modern Python (e.g., `Union[X, None]` to `X \| None`) |
| `B` | Catches common bugs like mutable default arguments |
| `SIM` | Suggests simpler code patterns (e.g., collapsing nested ifs) |

Usage:

```bash
uv run ruff check .       # Lint
uv run ruff check --fix . # Lint and auto-fix
uv run ruff format .      # Format
```

### 7. mypy — Static Type Checking

mypy performs static type analysis to catch type errors before runtime.

Configuration in `pyproject.toml`:

```toml
[tool.mypy]
python_version = "3.12"
strict = true
plugins = ["pydantic.mypy"]

[[tool.mypy.overrides]]
module = ["asyncpg.*", "uvicorn.*"]
ignore_missing_imports = true
```

What each setting does:

| Setting | Purpose |
| ------- | ------- |
| `strict = true` | Enables all optional strictness flags (no implicit `Any`, no untyped defs, etc.) |
| `plugins = ["pydantic.mypy"]` | Teaches mypy about Pydantic's `BaseModel` magic (field defaults, validators, `model_validate`) |
| `ignore_missing_imports` | Silences errors for third-party packages that don't ship type stubs (`asyncpg`, `uvicorn`) |

Usage:

```bash
uv run mypy app/
```

### 8. Docker + Docker Compose

#### Dockerfile (Multi-Stage Build)

**Stage 1 — Builder** (uses official `uv` image):

1. Copies `pyproject.toml` + `uv.lock` first and installs dependencies. This leverages Docker layer caching — dependencies are only reinstalled when the lockfile changes.
2. Copies the full source code and finalizes the install.

**Stage 2 — Runtime** (uses `python:3.12-slim-bookworm`):

- Copies only the `.venv`, application code, and Alembic files from the builder
- No UV, no build tools, no source control — keeps the final image small
- Sets `PATH` to include the venv's `bin/` directory

#### docker-compose.yml

```yaml
services:
  db:
    image: postgres:16-alpine
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U notetaker -d notetaker"]
      interval: 5s
      timeout: 5s
      retries: 5

  api:
    build: .
    depends_on:
      db:
        condition: service_healthy
```

Key design decisions:

- **`postgres:16-alpine`** — lightweight PostgreSQL image
- **Named volume (`pgdata`)** — data persists across container restarts
- **Health check** — `pg_isready` confirms Postgres is accepting connections
- **`depends_on: condition: service_healthy`** — the API container waits until the DB is healthy before starting
- **Shared `.env` file** — both services read the same environment variables

#### Container Startup Flow

```
docker compose up --build
  └─> db starts (postgres:16-alpine)
      └─> healthcheck passes (pg_isready)
          └─> api starts
              └─> alembic upgrade head (runs migrations)
                  └─> uvicorn app.main:app (serves the API)
```

## Development Commands

```bash
# Start the stack
docker compose up --build -d

# View logs
docker compose logs -f api

# Stop everything
docker compose down

# Stop and remove data
docker compose down -v

# Run linter locally
uv run ruff check .

# Run formatter locally
uv run ruff format .

# Run type checker locally
uv run mypy app/
```
