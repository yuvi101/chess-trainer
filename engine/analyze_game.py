import json
from pathlib import Path
import chess
import chess.engine
import os
import logging
from shared.db import get_connection
import time
import socket


# ------------------- CONFIG ----------------------
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_GAMES_DIR = DATA_DIR / "raw_games"
RESULTS_DIR = DATA_DIR / "engine_results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR = DATA_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
USERNAME = os.getenv("LICHESS_USERNAME")
if not USERNAME:
    raise RuntimeError("LICHESS_USERNAME environment variable is not set")

# ---------- Connect to Stockfish over TCP ----------
ENGINE_CMD = ["nc", "stockfish_engine", "3334"]

# ---------- Logging ----------
logging.basicConfig(
    filename=LOG_DIR / "analysis.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

console = logging.StreamHandler()
console.setLevel(logging.INFO)
logging.getLogger("").addHandler(console)
# --------------------------------
 

# def load_game(path):
#     with open(path, "r") as f:
#         return json.load(f)

def load_games_from_db():
    """Load games that haven't been analyzed yet from the past 7 days only."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT g.id, g.lichess_id, g.moves, g.color
        FROM games g
        WHERE g.played_at >= NOW() - INTERVAL '7 days'
            AND g.id NOT IN (SELECT DISTINCT game_id FROM moves)
        ORDER BY g.played_at DESC
    """)
    games = cur.fetchall()
    cur.close()
    conn.close()
    return games


def save_analysis_to_db(game_id, results):
    conn = get_connection()
    cur = conn.cursor()
    try:
        for r in results:
            cur.execute("""
                INSERT INTO moves (game_id, move_number, move_played, best_move, cp_loss, label)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                game_id,
                r["move_number"],
                r["move_played"],
                r["best_move"],
                r["cp_loss"],
                r["label"]
            ))

        conn.commit()
        logging.info(f"Saved analysis for game {game_id}")
    except Exception as e:
        conn.rollback()
        logging.error(f"Failed to save analysis for game {game_id}: {e}")
    finally:
        cur.close()
        conn.close()


def classify_move(cp_loss):
    if cp_loss < 50:
        return "Good"
    elif cp_loss < 150:
        return "Inaccuracy"
    elif cp_loss < 300:
        return "Mistake"
    else:
        return "Blunder"


def analyze_game(game_id, lichess_id, moves_str, color, engine):
    board = chess.Board()
    moves = moves_str.split()

    if not moves:
        logging.warning(f"Skipping game {lichess_id} — no moves found")
        return None

    my_color = chess.WHITE if color == "white" else chess.BLACK

    results = []
    total_cp_loss = 0
    total_blunders = 0

    for i, move in enumerate(moves):
        if board.turn == my_color:
            info_before = engine.analyse(board, chess.engine.Limit(depth=15))
            best_move = info_before["pv"][0]
            best_score = info_before["score"].pov(my_color).score(mate_score=10000)
            best_move_san = board.san(best_move)

            try:
                board.push_san(move)
            except Exception as e:
                logging.error(f"Illegal move {move} in game {lichess_id}: {e}")
                break

            info_after = engine.analyse(board, chess.engine.Limit(depth=15))
            after_score = info_after["score"].pov(my_color).score(mate_score=10000)

            cp_loss = max(0, best_score - after_score)
            label = classify_move(cp_loss)

            total_cp_loss += cp_loss
            if label == "Blunder":
                total_blunders += 1

            results.append({
                "move_number": (i // 2) + 1,
                "move_played": move,
                "best_move": best_move_san,
                "cp_loss": cp_loss,
                "label": label,
            })
        else:
            board.push_san(move)

    save_analysis_to_db(game_id, results)

    return {
        "total_cp_loss": total_cp_loss,
        "total_blunders": total_blunders,
        "moves_analyzed": len(results)
    }


def analyze_all_games():
    games = load_games_from_db()
    print(f"DEBUG: found {len(games)} unanalyzed games: {games}")
    if not games:
        logging.info("No unanalyzed games found.")
        return

    with chess.engine.SimpleEngine.popen_uci(ENGINE_CMD) as engine:
        for game_id, lichess_id, moves_str, color in games:
            logging.info(f"Analyzing game {lichess_id} ...")
            r = analyze_game(game_id, lichess_id, moves_str, color, engine)
            if r:
                logging.info(
                    f"Done — CP Loss: {r['total_cp_loss']} | "
                    f"Blunders: {r['total_blunders']} | "
                    f"Moves analyzed: {r['moves_analyzed']}"
                )


def wait_for_engine(retries=5, delay=2):
    for attempt in range(retries):
        try:
            with socket.create_connection(("stockfish_engine", 3334), timeout=3):
                logging.info("Stockfish engine is reachable.")
                return True
        except (ConnectionRefusedError, OSError):
            logging.warning(f"Engine not ready, retrying in {delay}s... (attempt {attempt + 1}/{retries})")
            time.sleep(delay)
    raise RuntimeError("Could not connect to Stockfish engine after multiple attempts.")


def main():
    wait_for_engine()
    analyze_all_games()


if __name__ == "__main__":
    main()