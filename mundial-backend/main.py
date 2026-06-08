import asyncio
import logging
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    # start the result-polling background task on boot
    task = asyncio.create_task(_poll_results())
    yield
    # cancel it cleanly on shutdown
    task.cancel()


app = FastAPI(
    title="Mundial Typer",
    version="0.1.0",
    lifespan=lifespan,
)


# allow the React dev server to call the API
# in prod we'll add the deployed frontend URL here too
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,           # needed for httpOnly auth cookies
    allow_methods=["*"],
    allow_headers=["*"],
)


# simple healthcheck used by tests and uptime monitoring
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


# --- background job: auto-score finished matches ---
# polls football-data.org every 5 min and calls finalize_match() for any
# match that moved to FINISHED since we last checked.
# runs only when FOOTBALL_API_KEY is set — silent no-op otherwise (tests).

_POLL_INTERVAL = 5 * 60   # seconds


async def _poll_results() -> None:
    # lazy import so the module-level import doesn't trigger during tests
    # where FOOTBALL_API_KEY isn't set
    import os
    if not os.getenv("FOOTBALL_API_KEY"):
        logger.info("FOOTBALL_API_KEY not set — skipping background job")
        return

    from db.queries import finalize_match, get_match_by_external_id, MatchAlreadyFinished, MatchNotFound
    from services.football_api import fetch_finished_matches

    while True:
        await asyncio.sleep(_POLL_INTERVAL)
        try:
            finished = fetch_finished_matches()
            for m in finished:
                row = get_match_by_external_id(m["external_id"])
                if row is None or row["status"] == "finished":
                    continue  # not in our DB yet, or already finalized
                if m["home_goals"] is None or m["away_goals"] is None:
                    continue  # API returned finished but no score yet
                try:
                    finalize_match(row["id"], m["home_goals"], m["away_goals"])
                    logger.info(
                        "auto-finalized match external_id=%s %s:%s",
                        m["external_id"], m["home_goals"], m["away_goals"],
                    )
                except MatchAlreadyFinished:
                    pass  # race condition — already done, ignore
                except MatchNotFound:
                    pass  # shouldn't happen but safe to skip
        except Exception as exc:
            # log and continue — never crash the background task
            # we'll retry in the next poll cycle (5 min)
            logger.warning("result poll failed: %s", exc)
