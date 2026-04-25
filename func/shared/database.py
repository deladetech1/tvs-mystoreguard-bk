import psycopg2
from psycopg2.extras import RealDictCursor
from shared.settings import DATABASE_URL


def get_db_connection():
    """Create a PostgreSQL connection from DATABASE_URL environment variable."""
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
