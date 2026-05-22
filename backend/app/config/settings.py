from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Optional

from dotenv import load_dotenv

load_dotenv()


def _get_streamlit_secret(key: str) -> Optional[str]:
    """Read a Streamlit secret only when running inside Streamlit."""
    try:
        import streamlit as st  # type: ignore

        if key in st.secrets:
            value = st.secrets[key]
            return str(value) if value is not None else None
    except Exception:
        return None
    return None


def get_setting(key: str, default: Optional[str] = None) -> Optional[str]:
    """Environment first, Streamlit secrets second, default last."""
    return os.getenv(key) or _get_streamlit_secret(key) or default


@dataclass(frozen=True)
class Settings:
    app_env: str = get_setting("APP_ENV", "local") or "local"
    log_level: str = get_setting("LOG_LEVEL", "INFO") or "INFO"

    woo_site_url: Optional[str] = get_setting("WOO_SITE_URL")
    woo_consumer_key: Optional[str] = get_setting("WOO_CONSUMER_KEY")
    woo_consumer_secret: Optional[str] = get_setting("WOO_CONSUMER_SECRET")

    supabase_db_url: Optional[str] = get_setting("SUPABASE_DB_URL")
    microsoft_client_id: Optional[str] = get_setting("MICROSOFT_CLIENT_ID")
    openai_api_key: Optional[str] = get_setting("OPENAI_API_KEY")


def get_settings() -> Settings:
    return Settings()
