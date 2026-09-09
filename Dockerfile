FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /uvx /usr/local/bin/

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1

COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-dev --no-install-project || uv sync --no-dev --no-install-project

COPY src/ ./src/
COPY alembic.ini ./
COPY alembic/ ./alembic/
COPY scripts/ ./scripts/
RUN chmod +x scripts/render-start.sh

# `python src/main.py` (script mode), not `-m src.main`: running as a
# script makes Python prepend the script's own directory (src/) to
# sys.path, which is what makes src/main.py's own absolute imports (e.g.
# `from bot.client import ShaheenBot`) resolve — bot/, core/, database/,
# etc. live inside src/, not at the repo root. `-m src.main` instead adds
# only the WORKDIR (the repo root) to sys.path, leaving those unresolved
# — see docs/DECISIONS.md ADR-057.
CMD ["uv", "run", "python", "src/main.py"]
