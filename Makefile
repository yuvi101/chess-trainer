# ---- Database ----
db-shell:
	docker compose exec postgres psql -U chess -d chess_db

db-reset:
	docker compose exec postgres psql -U chess -d chess_db -c "TRUNCATE moves, games CASCADE;"

db-status:
	docker compose exec postgres psql -U chess -d chess_db -c "SELECT lichess_id, color, opponent FROM games;"
	docker compose exec postgres psql -U chess -d chess_db -c "SELECT COUNT(*) as total_moves FROM moves;"

db-init:
	docker compose run --rm collector python -c "from shared.db import init_db; init_db()"

# ---- Services ----
up:
	docker compose up -d

down:
	docker compose down

build:
	docker compose build --no-cache

logs:
	docker compose logs -f

# ---- Pipeline ----
collect:
	docker compose run --rm collector python lichess_collector.py

analyze:
	docker compose run --rm analyzer python analyze_game.py

report:
	docker compose run --rm reporting python report_generator.py

open-report:
	xdg-open reports/$(shell ls reports/ | tail -1)

# ---- Full pipeline ----
run-all: db-reset collect analyze report open-report

# ---- Init ----
init:
	docker compose run --rm collector python -c "from shared.db import init_db; init_db()"