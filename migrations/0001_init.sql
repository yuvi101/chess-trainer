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

CREATE TABLE IF NOT EXISTS moves (
    id SERIAL PRIMARY KEY,
    game_id INTEGER REFERENCES games(id) ON DELETE CASCADE,
    move_number INTEGER,
    move_played VARCHAR(10),
    best_move VARCHAR(10),
    cp_loss INTEGER,
    label VARCHAR(20),
    analyzed_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS llm_reports (
    id SERIAL PRIMARY KEY,
    generated_at TIMESTAMP DEFAULT NOW(),
    content TEXT,
    tokens_used INTEGER,
    cost_usd NUMERIC(10, 6),
    latency_ms INTEGER
);

CREATE TABLE IF NOT EXISTS metrics (
    id SERIAL PRIMARY KEY,
    run_at TIMESTAMP DEFAULT NOW(),
    engine_runtime_ms INTEGER,
    games_analyzed INTEGER,
    failures INTEGER
);
