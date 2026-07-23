import psycopg2
import os
import logging
from pathlib import Path

DB_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "postgres"),
    "port": os.getenv("POSTGRES_PORT", 5432),
    "dbname": os.getenv("POSTGRES_DB", "chess_db"),
    "user": os.getenv("POSTGRES_USER", "chess"),
    "password": os.getenv("POSTGRES_PASSWORD", "chess"),
}

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"


def get_connection():
    return psycopg2.connect(**DB_CONFIG)


def run_migrations():
    """Apply any migrations in migrations/ that haven't been applied yet, in filename order."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            filename VARCHAR(255) PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT NOW()
        );
    """)
    conn.commit()

    cur.execute("SELECT filename FROM schema_migrations")
    applied = {row[0] for row in cur.fetchall()}

    pending = sorted(
        f for f in MIGRATIONS_DIR.glob("*.sql")
        if f.name not in applied
    )

    for migration in pending:
        logging.info(f"Applying migration {migration.name}...")
        cur.execute(migration.read_text())
        cur.execute(
            "INSERT INTO schema_migrations (filename) VALUES (%s)",
            (migration.name,)
        )
        conn.commit()
        logging.info(f"Applied migration {migration.name}.")

    if not pending:
        logging.info("No pending migrations.")

    cur.close()
    conn.close()


def init_db():
    """Bring the database schema up to date by applying any pending migrations."""
    run_migrations()
    logging.info("Database initialized successfully.")