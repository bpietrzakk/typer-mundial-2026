import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from db.connection import PoolBusy
from domain.sync_plan import is_sync_enabled
from routers import admin as admin_router
from routers import admin_bonus as admin_bonus_router
from routers import admin_sync as admin_sync_router
from routers import admin_users as admin_users_router
from routers import auth as auth_router
from routers import bonus as bonus_router
from routers import competitions as competitions_router
from routers import league_bonus as league_bonus_router
from routers import leagues as leagues_router
from routers import matches as matches_router
from routers import predictions as predictions_router
from routers import ranking as ranking_router
from services.sync import run_scheduler

# without this our info logs (sync runs) never show up, uvicorn only configures its own loggers
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
# httpx logs every request at info level, that is noise for the sync job
logging.getLogger("httpx").setLevel(logging.WARNING)

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

    task = None
    if is_sync_enabled(os.getenv("SYNC_ENABLED"), os.getenv("FOOTBALL_API_KEY")):
        task = asyncio.create_task(run_scheduler())
    else:
        logger.info("provider sync is off (SYNC_ENABLED=false or no FOOTBALL_API_KEY)")
    yield
    if task is not None:
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


@app.exception_handler(PoolBusy)
async def pool_busy_handler(_request: Request, _exc: PoolBusy) -> JSONResponse:
    # every db connection stayed busy too long — tell the client to retry
    return JSONResponse(status_code=503, content={"detail": "Serwer jest chwilowo przeciążony, spróbuj ponownie"})


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(auth_router.router)
app.include_router(matches_router.router)
app.include_router(predictions_router.router)
app.include_router(admin_router.router)
app.include_router(admin_bonus_router.router)
app.include_router(admin_sync_router.router)
app.include_router(admin_users_router.router)
app.include_router(ranking_router.router)
app.include_router(leagues_router.router)
app.include_router(bonus_router.router)
app.include_router(league_bonus_router.router)
app.include_router(competitions_router.router)
