import psycopg2
from psycopg2.extras import RealDictCursor
from shared.settings import DB_URL


def get_db_connection():
    """Create a PostgreSQL connection from DB_URL environment variable."""
    return psycopg2.connect(DB_URL, cursor_factory=RealDictCursor)
