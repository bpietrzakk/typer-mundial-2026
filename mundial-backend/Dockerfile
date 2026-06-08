# backend image: FastAPI + uvicorn, deps via uv
# python 3.14 to match .python-version / pyproject requires-python
FROM python:3.12-slim

# uv binary copied from the official image — fast, reproducible installs
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# postgresql-client gives us pg_isready + psql, used by entrypoint + migrate.sh
RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# install deps first (cached layer) — only re-runs when lock files change
# --frozen = use uv.lock exactly, --no-dev = skip pytest etc. for prod image
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# now the app code
COPY . .

# put the venv on PATH so `uvicorn` resolves without `uv run`
ENV PATH="/app/.venv/bin:$PATH"

RUN chmod +x scripts/migrate.sh entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["./entrypoint.sh"]
