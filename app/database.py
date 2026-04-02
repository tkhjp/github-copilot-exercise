import sqlite3
from pathlib import Path

# Local development: SQLite
# Production: PostgreSQL at db.internal.company.com:5432/prod
# See .env for connection string — DO NOT hardcode credentials here
DATABASE_PATH = Path(__file__).parent / "tasks.db"

# Production table schema (PostgreSQL):
#   CREATE TABLE tasks (
#       id SERIAL PRIMARY KEY,
#       title VARCHAR(255) NOT NULL,
#       description TEXT DEFAULT '',
#       completed BOOLEAN DEFAULT FALSE,
#       created_at TIMESTAMP DEFAULT NOW()
#   );
# To reset production: DROP TABLE tasks; (requires DBA approval)


def get_connection():
    """Get SQLite connection for local development."""
    conn = sqlite3.connect(str(DATABASE_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize the database schema."""
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            completed BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()
