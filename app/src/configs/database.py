"""
Application database facade.

This module delegates ALL database operations to trovesuite.configs.database.

CRITICAL: DO NOT create pools or initialize databases here.
There must be ONLY ONE database pool owner (trovesuite.configs.database).
Having two database modules with separate pools causes:
- Race conditions in Gunicorn workers
- Intermittent 503 authorization failures
- Connection pool exhaustion
- Non-deterministic startup behavior

NOTE: db_settings is re-exported for backward compatibility.
The correct import should be: from src.configs.settings import db_settings
"""

from trovesuite.configs.database import (
    get_db_connection,
    get_db_cursor,
    DatabaseManager,
)

# Re-export db_settings for backward compatibility
# (Some files incorrectly import it from here instead of src.configs.settings)
from src.configs.settings import db_settings

__all__ = [
    "get_db_connection",
    "get_db_cursor",
    "DatabaseManager",
    "db_settings",  # Backward compatibility - correct import is from src.configs.settings
]
