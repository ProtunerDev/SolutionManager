import psycopg2.pool
import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)

_pool = None


def init_pool(app):
    global _pool
    db_config = {
        'host': app.config.get('DB_HOST', 'localhost'),
        'port': app.config.get('DB_PORT', 5432),
        'database': app.config.get('DB_NAME', 'SolutionManager'),
        'user': app.config.get('DB_USER', 'postgres'),
        'password': app.config.get('DB_PASSWORD', '')
    }
    _pool = psycopg2.pool.ThreadedConnectionPool(minconn=2, maxconn=10, **db_config)
    logger.info("Database connection pool initialized (min=2, max=10)")


def get_connection():
    if _pool is None:
        raise RuntimeError("Connection pool not initialized — call init_pool(app) at startup")
    return _pool.getconn()


def return_connection(conn):
    if _pool and conn:
        _pool.putconn(conn)


@contextmanager
def pooled_connection():
    """Context manager: borrows a connection from the pool and returns it when done."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        return_connection(conn)
