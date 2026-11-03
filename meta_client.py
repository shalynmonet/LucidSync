"""Single entry point for future Meta Model API calls.

Endpoints and request formats will be added after the Meta API documentation is
provided. This module intentionally makes no network requests in the scaffold.
"""

import os

from dotenv import load_dotenv

load_dotenv()

META_API_KEY = os.getenv("META_API_KEY", "")
MOCK_MODE = os.getenv("MOCK_MODE", "true").strip().lower() in {"1", "true", "yes", "on"}


def require_live_api_key() -> str:
    """Return the configured key or raise a clear error for live API use."""
    if not META_API_KEY:
        raise RuntimeError(
            "META_API_KEY is missing. Add it to your local .env file to use live models."
        )
    return META_API_KEY
