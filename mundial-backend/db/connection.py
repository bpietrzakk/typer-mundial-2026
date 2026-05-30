import os

from dotenv import load_dotenv
from psycopg2 import pool

# load env variables so we have db credentials
load_dotenv()

# read connection params from env — defaults match .env.example
_host     = os.getenv("POSTGRES_HOST", "localhost")
_port     = os.getenv("POSTGRES_PORT", "5432")
_user     = os.getenv("POSTGRES_USER", "typer")
_password = os.getenv("POSTGRES_PASSWORD", "typer")
_dbname   = os.getenv("POSTGRES_DB", "typer")

# create connection pool at startup
# minconn=1 keeps one connection ready at all times
# maxconn=5 allows up to 5 simultaneous db connections
_pool = pool.SimpleConnectionPool(
    minconn=1,
    maxconn=5,
    host=_host,
    port=_port,
    user=_user,
    password=_password,
    dbname=_dbname,
)


def get_conn():
    # borrow a free connection from the pool
    return _pool.getconn()


def release_conn(conn) -> None:
    # return the connection back to the pool so others can use it
    _pool.putconn(conn)
