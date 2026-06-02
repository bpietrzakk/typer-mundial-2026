from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import admin as admin_router
from routers import auth as auth_router
from routers import matches as matches_router
from routers import predictions as predictions_router
from routers import ranking as ranking_router


app = FastAPI(
    title="Mundial Typer",
    version="0.1.0",
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
app.include_router(ranking_router.router)
# more routers will land here: leagues, bonus
