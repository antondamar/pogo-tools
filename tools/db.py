import os
from contextlib import contextmanager
from threading import Lock

from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import ThreadedConnectionPool

load_dotenv()

# DB_URL = os.getenv("LOCAL_DATABASE_URL")
DB_URL = os.getenv("NEON_DATABASE_URL")

_MIN_CONN = 1
_MAX_CONN = 5

_pool = None
_pool_lock = Lock()


def _get_pool():
    global _pool
    if _pool is None:
        with _pool_lock:
            if _pool is None:
                _pool = ThreadedConnectionPool(
                    _MIN_CONN,
                    _MAX_CONN,
                    DB_URL,
                    cursor_factory=RealDictCursor,
                )
    return _pool


@contextmanager
def get_db_connection():
    pool = _get_pool()
    conn = pool.getconn()
    try:
        if conn.closed:
            pool.putconn(conn, close=True)
            conn = pool.getconn()
        yield conn
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except psycopg2.Error:
            pool.putconn(conn, close=True)
            conn = None
        raise
    finally:
        if conn is not None:
            pool.putconn(conn)
