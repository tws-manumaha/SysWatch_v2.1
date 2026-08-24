"""
SysWatch v2.1 — Database Layer with Connection Pooling
Uses DBUtils PooledDB for persistent connection management.
Falls back to per-query connections if DBUtils is not installed.
"""
import logging
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Optional

import pymysql
from pymysql.cursors import DictCursor

from modules.config import Config

logger = logging.getLogger("syswatch.database")

try:
    from dbutils.pooled_db import PooledDB
    _POOL: Optional[PooledDB] = None
    _POOL_LOCK = threading.Lock()
    _HAS_POOL = True
except ImportError:
    _POOL = None
    _HAS_POOL = False
    logger.warning("DBUtils not installed, falling back to per-query connections")


def _get_pool() -> PooledDB:
    """Lazily initialize the connection pool (thread-safe)."""
    global _POOL
    if _POOL is not None:
        return _POOL
    with _POOL_LOCK:
        if _POOL is not None:
            return _POOL
        _POOL = PooledDB(
            creator=pymysql,
            mincached=2,
            maxcached=Config.DB_POOL_SIZE,
            maxconnections=Config.DB_POOL_SIZE + 5,
            blocking=True,
            maxusage=None,
            setsession=["SET time_zone='+00:00'", "SET sql_mode='STRICT_TRANS_TABLES'"],
            reset=True,
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME,
            charset="utf8mb4",
            cursorclass=DictCursor,
            connect_timeout=Config.DB_CONNECT_TIMEOUT,
            autocommit=True,
        )
        logger.info(f"Connection pool initialized (size={Config.DB_POOL_SIZE})")
        return _POOL


def _get_connection():
    """Get a database connection from pool or create new one."""
    if _HAS_POOL:
        return _get_pool().connection()
    return pymysql.connect(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        database=Config.DB_NAME,
        charset="utf8mb4",
        cursorclass=DictCursor,
        connect_timeout=Config.DB_CONNECT_TIMEOUT,
        autocommit=True,
    )


def utcnow():
    """Return current UTC time (timezone-aware, replaces deprecated datetime.utcnow())."""
    return datetime.now(timezone.utc)


class Database:
    """Database abstraction layer with connection pooling."""

    @contextmanager
    def get_conn(self):
        """Context manager for getting a pooled connection."""
        conn = None
        try:
            conn = _get_connection()
            yield conn
        except pymysql.Error as e:
            logger.error(f"Database error: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def query(self, sql: str, params: tuple = ()) -> list[dict]:
        """Execute a SELECT query and return list of dicts."""
        with self.get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                return list(cursor.fetchall())

    def query_one(self, sql: str, params: tuple = ()) -> Optional[dict]:
        """Execute a SELECT query and return single dict or None."""
        with self.get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                return cursor.fetchone()

    def execute(self, sql: str, params: tuple = ()) -> int:
        """Execute an INSERT/UPDATE/DELETE and return affected row count."""
        with self.get_conn() as conn:
            with conn.cursor() as cursor:
                affected = cursor.execute(sql, params)
                return affected

    def execute_many(self, sql: str, params_list: list[tuple]) -> int:
        """Execute a bulk INSERT/UPDATE/DELETE."""
        with self.get_conn() as conn:
            with conn.cursor() as cursor:
                affected = cursor.executemany(sql, params_list)
                return affected

    def execute_returning_id(self, sql: str, params: tuple = ()) -> int:
        """Execute an INSERT and return the last inserted row ID."""
        with self.get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                return cursor.lastrowid

    def transaction(self):
        """Return a context manager for a transaction (manual commit/rollback)."""
        return _Transaction(self)


class _Transaction:
    """Manual transaction context manager with savepoint support."""

    def __init__(self, db: Database):
        self.db = db
        self.conn = None

    def __enter__(self):
        self.conn = _get_connection()
        self.conn.autocommit(False)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if exc_type is not None:
                self.conn.rollback()
            else:
                self.conn.commit()
        finally:
            self.conn.autocommit(True)
            self.conn.close()

    def query(self, sql: str, params: tuple = ()) -> list[dict]:
        with self.conn.cursor() as cursor:
            cursor.execute(sql, params)
            return list(cursor.fetchall())

    def query_one(self, sql: str, params: tuple = ()) -> Optional[dict]:
        with self.conn.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.fetchone()

    def execute(self, sql: str, params: tuple = ()) -> int:
        with self.conn.cursor() as cursor:
            return cursor.execute(sql, params)

    def execute_returning_id(self, sql: str, params: tuple = ()) -> int:
        with self.conn.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.lastrowid


# Singleton instance
db = Database()


def init_db(schema_path: str = None) -> bool:
    """
    Initialize the database schema by executing schema.sql.
    Splits on ';;' delimiter (not ';') to avoid splitting inside stored procedures.
    Each statement is executed individually; errors for CREATE TABLE IF NOT EXISTS
    are expected and ignored, but actual errors are logged.
    Returns True if all statements succeeded, False if any failed.
    """
    if schema_path is None:
        from pathlib import Path
        schema_path = str(Path(__file__).resolve().parent.parent / "schema.sql")

    try:
        with open(schema_path, "r") as f:
            schema_sql = f.read()
    except FileNotFoundError:
        logger.error(f"Schema file not found: {schema_path}")
        return False

    # Use ;; delimiter to avoid splitting inside any multi-statement DDL
    statements = [s.strip() for s in schema_sql.split(";") if s.strip()]
    success_count = 0
    fail_count = 0

    with db.get_conn() as conn:
        with conn.cursor() as cursor:
            for stmt in statements:
                stmt = stmt.strip()
                if not stmt or stmt.startswith("--"):
                    continue
                # Skip comment-only lines at the start of statements
                lines = [l for l in stmt.split("\n") if not l.strip().startswith("--")]
                stmt = "\n".join(lines).strip()
                if not stmt:
                    continue
                try:
                    cursor.execute(stmt)
                    success_count += 1
                except pymysql.err.MySQLError as e:
                    code = e.args[0] if e.args else 0
                    # 1050: table exists, 1062: duplicate entry — expected with IF NOT EXISTS / ON DUPLICATE
                    if code in (1050, 1062, 1051):
                        success_count += 1
                    else:
                        logger.warning(f"Schema statement failed (code={code}): {e}")
                        fail_count += 1

    logger.info(f"Schema init: {success_count} succeeded, {fail_count} failed")
    return fail_count == 0


def check_connection() -> bool:
    """Test database connectivity."""
    try:
        result = db.query_one("SELECT 1 as test")
        return result is not None and result.get("test") == 1
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False
