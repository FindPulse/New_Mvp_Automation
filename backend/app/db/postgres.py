from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator, Optional, Any

from backend.app.config.settings import get_settings


@contextmanager
def get_postgres_connection(db_url: Optional[str] = None) -> Iterator[Any]:
    """Open and close a Postgres/Supabase connection safely.

    psycopg2 is imported lazily so unit tests that do not hit Postgres can run without a live DB driver.
    """
    try:
        import psycopg2  # type: ignore
    except ImportError as exc:
        raise RuntimeError("psycopg2 is required for Postgres/Supabase access. Install backend requirements.") from exc

    resolved_url = db_url or get_settings().supabase_db_url
    if not resolved_url:
        raise RuntimeError("SUPABASE_DB_URL is missing.")

    conn = psycopg2.connect(resolved_url)
    try:
        yield conn
    finally:
        conn.close()
