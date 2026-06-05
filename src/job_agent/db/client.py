"""Thin Supabase client wrapper with dependency injection (adapted from reference).

DI pattern: pass ``client`` in tests to avoid live calls. When omitted, the wrapper
calls ``settings.require_db_credentials()`` then builds the real client. The
``supabase`` import is lazy so this module is import-safe and offline tests need no
``supabase`` package installed.
"""

from __future__ import annotations

from typing import Any

from job_agent.config import Settings, get_settings


class SupabaseClient:
    def __init__(self, settings: Settings | None = None, client: Any | None = None) -> None:
        if client is not None:
            self._client = client
            return
        _settings = settings if settings is not None else get_settings()
        _settings.require_db_credentials()
        from supabase import create_client  # lazy import

        self._client = create_client(_settings.supabase_url, _settings.supabase_key)

    @property
    def raw(self) -> Any:
        """The underlying Supabase client for direct table access."""
        return self._client
