# Chess trainer

# ♟️ Chess Game Intelligence Agent Platform

An AI-powered platform that analyzes your Lichess games with Stockfish, generates personalized weekly coaching reports using LLMs, and tracks your improvement over time with full observability.

Example of a generated report:
![Coaching Report](docs/report.png)

## 🎯 What It Does

Every week, this platform:

1. **Pulls your games** from Lichess API
2. **Analyzes each move** with Stockfish (depth 20)
3. **Identifies patterns** — blunders, mistakes, opening weaknesses
4. **Generates a coaching report** using Gemini AI with personalized feedback
5. **Tracks metrics** — cost per run, blunder rate over time, LLM latency
6. **Sends you an HTML report** with board diagrams for every mistake

It's like having a personal chess coach who never sleeps.

---

## 🚀 Features

### Chess Analysis
- Stockfish engine integration over TCP (multi-stage Docker build)
- Classifies moves: Good / Inaccuracy / Mistake / Blunder
- Stores analysis in PostgreSQL for historical tracking
- Generates SVG board diagrams for every significant position

### AI Coaching
- LLM-powered (Gemini/Claude (optional)) personalized coaching reports
- Identifies recurring patterns across multiple games
- Suggests training plans based on your actual weaknesses
- References specific games: "In Game 2 vs player123, move 15..."

### Observability Stack
- **Prometheus** — tracks pipeline health, cost, latency
- **Grafana** — visualizes trends over time
- **Cost tracking** — every LLM call logged with token count and USD cost
- **Failure monitoring** — know immediately when a stage breaks

### Automation
- **Celery Beat** — runs collection + analysis + reporting on a schedule
- **Redis** — message broker for task queue
- **Docker Compose** — entire stack in one command

**Services:**
- `postgres` — stores games, moves, LLM reports, metrics
- `stockfish` — chess engine exposed via socat TCP bridge
- `collector` — fetches games from Lichess API
- `analyzer` — runs Stockfish analysis on each game
- `reporter` — generates LLM coaching reports with board diagrams
- `celery` — scheduler for automated runs
- `redis` — message broker
- `prometheus` — metrics storage
- `grafana` — metrics visualization
- `pushgateway` — receives metrics from batch jobs

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Language** | Python 3.11 |
| **Chess Engine** | Stockfish (compiled from source) |
| **LLM** | Gemini 1.5 Flash (free tier) |
| **Database** | PostgreSQL 16 |
| **Scheduler** | Celery + Redis |
| **Observability** | Prometheus + Grafana |
| **Containerization** | Docker + Docker Compose |
| **Networking** | socat TCP bridge for engine communication |

---

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Lichess account
- Gemini API key (free at https://aistudio.google.com)

### Setup

1. **Clone the repo**
```bash
git clone https://github.com/yourusername/chess-trainer.git
cd chess-trainer
```

2. **Set environment variables**
```bash
cat > .env << EOF
LICHESS_USERNAME=your_username
GEMINI_API_KEY=your_key_here
LLM_PROVIDER=gemini
EOF
```

3. **Start the stack**
```bash
docker compose up -d
```

4. **Initialize the database**
```bash
docker compose run --rm collector python -c "from shared.db import init_db; init_db()"
```

5. **Run the pipeline**
```bash
# Collect games
docker compose run --rm collector python lichess_collector.py

# Analyze games
docker compose run --rm analyzer python analyze_game.py

# Generate report
docker compose run --rm reporting python report_generator.py
```

6. **View your report**
```bash
open reports/report_$(date +%Y%m%d).html
```

7. **View metrics**
- Grafana: http://localhost:3000
- Prometheus: http://localhost:9090
- Pushgateway: http://localhost:9091

---

## 📅 Automated Schedule

By default, the pipeline runs:
- **Twice a week** (Monday & Thursday at 8:00 AM)
- **Report generation** (Friday at 9:00 AM)

Edit `scheduler/celery_app.py` to customize.

---

## 📊 Metrics Tracked

##### Some of the metrics:
| Metric | Description |
|---|---|
| `games_analyzed_total` | Games analyzed per run |
| `blunders_total` | Total blunders found |
| `llm_cost_usd_total` | Cumulative LLM cost |
| `llm_tokens_total` | Cumulative tokens used |
| `llm_request_duration_seconds` | LLM latency |
| `analysis_duration_seconds` | Stockfish runtime |

##### Snapshot of Grafana dashboard:
![example dashboard](docs/dashboard.png)
---



## 🙏 Acknowledgments

- [Stockfish](https://stockfishchess.org/) — the world's strongest open-source chess engine
- [Lichess](https://lichess.org/) — free, open-source chess platform with a great API
- [python-chess](https://python-chess.readthedocs.io/) — excellent chess library

---