import psycopg2
import os
import logging

DB_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "postgres"),
    "port": os.getenv("POSTGRES_PORT", 5432),
    "dbname": os.getenv("POSTGRES_DB", "chess_db"),
    "user": os.getenv("POSTGRES_USER", "chess"),
    "password": os.getenv("POSTGRES_PASSWORD", "chess"),
}


def get_connection():
    return psycopg2.connect(**DB_CONFIG)


def init_db():
    """Create tables if they don't exist."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS games (
            id SERIAL PRIMARY KEY,
            lichess_id VARCHAR(20) UNIQUE NOT NULL,
            played_at TIMESTAMP,
            opening VARCHAR(100),
            color VARCHAR(5),
            result VARCHAR(10),
            time_control VARCHAR(20),
            moves TEXT,
            opponent VARCHAR(50)
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS moves (
            id SERIAL PRIMARY KEY,
            game_id INTEGER REFERENCES games(id) ON DELETE CASCADE,
            move_number INTEGER,
            move_played VARCHAR(10),
            best_move VARCHAR(10),
            cp_loss INTEGER,
            label VARCHAR(20)
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS llm_reports (
            id SERIAL PRIMARY KEY,
            generated_at TIMESTAMP DEFAULT NOW(),
            content TEXT,
            tokens_used INTEGER,
            cost_usd NUMERIC(10, 6),
            latency_ms INTEGER
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS metrics (
            id SERIAL PRIMARY KEY,
            run_at TIMESTAMP DEFAULT NOW(),
            engine_runtime_ms INTEGER,
            games_analyzed INTEGER,
            failures INTEGER
        );
    """)

    conn.commit()
    cur.close()
    conn.close()
    logging.info("Database initialized successfully.")