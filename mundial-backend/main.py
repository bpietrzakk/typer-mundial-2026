import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import admin as admin_router
from routers import admin_bonus as admin_bonus_router
from routers import admin_users as admin_users_router
from routers import auth as auth_router
from routers import bonus as bonus_router
from routers import leagues as leagues_router
from routers import matches as matches_router
from routers import predictions as predictions_router
from routers import ranking as ranking_router


logger = logging.getLogger(__name__)


def _wait_for_db(max_attempts: int = 30) -> None:
    """Retry until PostgreSQL is accepting connections (needed in Docker)."""
    for attempt in range(1, max_attempts + 1):
        try:
            from db.connection import get_conn, release_conn
            conn = get_conn()
            release_conn(conn)
            logger.info("database ready")
            return
        except Exception as exc:
            logger.info("waiting for db (attempt %d/%d): %s", attempt, max_attempts, exc)
            time.sleep(2)
    raise RuntimeError("database not available after 60 s")


def run_migrations() -> None:
    """Apply pending SQL migrations — logic lives in db/migrate.py."""
    from db.migrate import run_migrations as apply_pending

    apply_pending()


@asynccontextmanager
async def lifespan(app: FastAPI):
    _wait_for_db()
    run_migrations()

    task = asyncio.create_task(_poll_results())
    yield
    task.cancel()


app = FastAPI(
    title="Mundial Typer",
    version="0.1.0",
    lifespan=lifespan,
)


# FRONTEND_URL can be comma-separated for multiple origins (dev + prod)
# e.g. FRONTEND_URL=http://localhost:5173,https://mundialtyper.vercel.app
_allowed_origins = [
    o.strip()
    for o in os.getenv("FRONTEND_URL", "http://localhost:5173").split(",")
    if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(auth_router.router)
app.include_router(matches_router.router)
app.include_router(predictions_router.router)
app.include_router(admin_router.router)
app.include_router(admin_bonus_router.router)
app.include_router(admin_users_router.router)
app.include_router(ranking_router.router)
app.include_router(leagues_router.router)
app.include_router(bonus_router.router)


_POLL_INTERVAL = 5 * 60  # seconds


async def _poll_results() -> None:
    if not os.getenv("FOOTBALL_API_KEY"):
        logger.info("FOOTBALL_API_KEY not set — skipping background job")
        return

    from db.queries import finalize_match, get_match_by_external_id, MatchAlreadyFinished, MatchNotFound
    from services.football_api import fetch_finished_matches

    while True:
        await asyncio.sleep(_POLL_INTERVAL)
        try:
            for m in fetch_finished_matches():
                row = get_match_by_external_id(m["external_id"])
                if row is None or row["status"] == "finished":
                    continue
                if m["home_goals"] is None or m["away_goals"] is None:
                    continue
                try:
                    finalize_match(row["id"], m["home_goals"], m["away_goals"])
                    logger.info("auto-finalized %s %s:%s", m["external_id"], m["home_goals"], m["away_goals"])
                except (MatchAlreadyFinished, MatchNotFound):
                    pass
        except Exception as exc:
            logger.warning("result poll failed: %s", exc)
