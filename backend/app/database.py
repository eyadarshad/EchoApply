import logging
import asyncio
from contextlib import asynccontextmanager
from psycopg_pool import AsyncConnectionPool
from app.config import settings

logger = logging.getLogger(__name__)

class AsyncCursorWrapper:
    def __init__(self, sync_cursor):
        self.sync_cursor = sync_cursor

    async def execute(self, query, params=None):
        await asyncio.to_thread(self.sync_cursor.execute, query, params)
        return self

    async def fetchone(self):
        return await asyncio.to_thread(self.sync_cursor.fetchone)

    async def fetchall(self):
        return await asyncio.to_thread(self.sync_cursor.fetchall)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await asyncio.to_thread(self.sync_cursor.close)

    def __getattr__(self, name):
        return getattr(self.sync_cursor, name)


class AsyncConnectionWrapper:
    def __init__(self, sync_conn):
        self.sync_conn = sync_conn

    def cursor(self):
        return AsyncCursorWrapper(self.sync_conn.cursor())

    async def commit(self):
        await asyncio.to_thread(self.sync_conn.commit)

    async def rollback(self):
        await asyncio.to_thread(self.sync_conn.rollback)

    async def close(self):
        await asyncio.to_thread(self.sync_conn.close)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    def __getattr__(self, name):
        return getattr(self.sync_conn, name)


# Singleton pool instance
pool = None

async def check_connection(conn):
    """Health check: runs a fast query to ensure connection is alive."""
    await conn.execute("SELECT 1;")

def init_pool():
    global pool
    if not settings.DATABASE_URL:
        logger.warning("DATABASE_URL is not set. Database pool initialization skipped.")
        return
    try:
        conninfo = settings.DATABASE_URL
        if settings.ENVIRONMENT == "production":
            if "sslmode=" not in conninfo:
                sep = "&" if "?" in conninfo else "?"
                conninfo += f"{sep}sslmode=require"
            if "connect_timeout=" not in conninfo:
                sep = "&" if "?" in conninfo else "?"
                conninfo += f"{sep}connect_timeout=10"
        else:
            if "connect_timeout=" not in conninfo:
                sep = "&" if "?" in conninfo else "?"
                conninfo += f"{sep}connect_timeout=3"

        pool = AsyncConnectionPool(
            conninfo=conninfo,
            min_size=5,
            max_size=20,
            timeout=10.0,
            open=False,  # Opened asynchronously in lifecycle startup
            check=check_connection
        )
    except Exception as e:
        logger.error(f"Failed to create AsyncConnectionPool: {e}")

async def startup_db():
    global pool
    if pool is None:
        init_pool()
    if pool:
        logger.info("Opening database connection pool...")
        await pool.open()

async def shutdown_db():
    global pool
    if pool:
        logger.info("Closing database connection pool...")
        await pool.close()

@asynccontextmanager
async def get_db():
    """Async context manager for yielding database connections from the pool."""
    global pool
    if pool is not None:
        try:
            async with pool.connection() as conn:
                yield conn
                return
        except Exception as e:
            logger.warning(f"Failed to get connection from pool: {e}. Trying fallback...")
            
    # Fallback to direct raw connection (e.g. for unit tests where pool is not opened/configured)
    logger.warning("Database pool is uninitialized or failed. Attempting direct fallback connection...")
    conn = None
    try:
        from app.main import psycopg
        sync_conn = psycopg.connect(settings.DATABASE_URL, connect_timeout=5)
        conn = AsyncConnectionWrapper(sync_conn)
    except Exception as e:
        logger.error(f"Fallback connection failed to open: {e}")
        
    try:
        yield conn
    finally:
        if conn:
            try:
                await conn.close()
            except Exception:
                pass

async def get_db_dep():
    """FastAPI dependency for yielding database connections."""
    async with get_db() as conn:
        yield conn
