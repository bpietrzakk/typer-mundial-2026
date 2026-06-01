from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


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


# routers will be registered here as we build them out
# (auth, matches, predictions, ranking, leagues, bonus, admin)
