import json
from pathlib import Path
import chess
import chess.engine
import os
import logging
from shared.db import get_connection
import time
import socket
from shared.metrics import push_metrics


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
    """Load games that haven't been analyzed yet."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT g.id, g.lichess_id, g.moves, g.color
        FROM games g
        WHERE g.id NOT IN (SELECT DISTINCT game_id FROM moves)
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

def get_cp(score, color):
    s = score.pov(color)
    if s.is_mate():
        return 10000 if s.mate() > 0 else -10000
    return s.score()

def analyze_game(game_id, lichess_id, moves_str, color, engine):
    board = chess.Board()
    moves = moves_str.split()

    if not moves:
        logging.warning(f"Skipping game {lichess_id} — no moves found")
        return None

    my_color = chess.WHITE if color == "white" else chess.BLACK

    results = []
    total_blunders = 0
    total_mistakes = 0
    total_inaccuracies = 0
    total_good_moves = 0
    total_cp_loss = 0
    
    depth = 20
    # Get starting evaluation
    info_start = engine.analyse(board, chess.engine.Limit(depth=depth))
    start_eval = info_start["score"].pov(my_color).score(mate_score=1000)
    
    end_eval = None
    my_moves = 0

    for i, move in enumerate(moves):
        if board.turn == my_color:
            info_before = engine.analyse(board, chess.engine.Limit(depth=depth))
            best_move = info_before["pv"][0]
            #best_score = info_before["score"].pov(my_color).score(mate_score=1000)
            best_score = get_cp(info_before["score"], my_color)
            best_move_san = board.san(best_move)
            my_moves += 1

            try:
                board.push_san(move)
            except Exception as e:
                logging.error(f"Illegal move {move} in game {lichess_id}: {e}")
                break
            info_after = engine.analyse(board, chess.engine.Limit(depth=depth))
            after_score = info_after["score"].pov(my_color).score(mate_score=10000)

            cp_loss = max(0, best_score - after_score)
            label = classify_move(cp_loss)
            total_cp_loss += cp_loss

            if label == "Blunder":
                total_blunders += 1
            elif label == "Mistake":
                total_mistakes += 1
            elif label == "Inaccuracy":
                total_inaccuracies += 1
            elif label == "Good":
                total_good_moves += 1

            results.append({
                "move_number": (i // 2) + 1,
                "move_played": move,
                "best_move": best_move_san,
                #"cp_loss": cp_loss,
                "cp_loss": total_cp_loss,
                "label": label,
            })
            
        else:
            board.push_san(move)
    # Save to DB

    save_analysis_to_db(game_id, results)

    return {
        "total_cp_loss": total_cp_loss,
        "total_blunders": total_blunders,
        "total_mistakes": total_mistakes,
        "total_inaccuracies": total_inaccuracies,
        "total_good_moves": total_good_moves,
        "moves_analyzed": len(results)
    }


def analyze_all_games():
    games = load_games_from_db()
    if not games:
        logging.info("No unanalyzed games found.")
        return
    
    total_analyzed = 0
    total_blunders = 0
    total_failures = 0
    total_duration = 0
    engine_crash_count = 0
    timeout_count = 0
    unknown_error_count = 0
    total_moves_analyzed = 0
    total_mistakes = 0
    total_inaccuracies = 0
    total_good_moves = 0
    total_cp_loss_all_games = 0

    with chess.engine.SimpleEngine.popen_uci(ENGINE_CMD) as engine:
        for game_id, lichess_id, moves_str, color in games:
            logging.info(f"Analyzing game {lichess_id} ...")
            start = time.time()

            try:
                r = analyze_game(game_id, lichess_id, moves_str, color, engine)
                duration = time.time() - start
                total_duration += duration
                if r:
                    total_analyzed += 1
                    total_blunders += r["total_blunders"]
                    total_mistakes += r.get("total_mistakes", 0)
                    total_inaccuracies += r.get("total_inaccuracies", 0)
                    total_good_moves += r.get("total_good_moves", 0)
                    total_moves_analyzed += r["moves_analyzed"]
                    #total_cp_loss_all_games += r["total_cp_loss"]
                    total_cp_loss_all_games += (r["total_cp_loss"] / r["moves_analyzed"])
                    logging.info(
                        # f"Done — CP Loss: {r['total_cp_loss']} | "
                        f"Done — CP Loss: {r['total_cp_loss'] / r['moves_analyzed']:.2f} | "
                        f"Blunders: {r['total_blunders']} | "
                        f"Moves analyzed: {r['moves_analyzed']}"
                        f"Duration: {duration:.2f}s"
                    )

            except chess.engine.EngineTerminatedError as e:
                logging.error(f"Engine crashed on game {lichess_id}: {e}")
                total_failures += 1
                engine_crash_count += 1  # track this separately
            
            except TimeoutError as e:
                logging.error(f"Engine timeout on game {lichess_id}: {e}")
                total_failures += 1
                timeout_count += 1  # track this separately
            
            except Exception as e:
                logging.error(f"Unknown error analyzing game {lichess_id}: {e}")
                total_failures += 1
                unknown_error_count += 1  # track this separately

    # Calculate averages
    avg_cp_loss_per_game = (total_cp_loss_all_games / total_analyzed) if total_analyzed > 0 else 0
    avg_cp_loss_per_move = (total_cp_loss_all_games / total_moves_analyzed) if total_moves_analyzed > 0 else 0

    # Calculate percentages
    blunder_rate = (total_blunders / total_moves_analyzed * 100) if total_moves_analyzed > 0 else 0
    mistake_rate = (total_mistakes / total_moves_analyzed * 100) if total_moves_analyzed > 0 else 0
    inaccuracy_rate = (total_inaccuracies / total_moves_analyzed * 100) if total_moves_analyzed > 0 else 0
    accuracy_rate = (total_good_moves / total_moves_analyzed * 100) if total_moves_analyzed > 0 else 0


    
    push_metrics("analyzer", {
        "games_analyzed_total": total_analyzed,
        "blunders_total": total_blunders,
        "mistakes_total": total_mistakes,
        "inaccuracies_total": total_inaccuracies,
        "good_moves_total": total_good_moves,
        "moves_analyzed_total": total_moves_analyzed,
        "analysis_duration_seconds": total_duration,
        "engine_crash_errors_total": engine_crash_count,
        "engine_timeout_errors_total": timeout_count,
        "unknown_errors_total": unknown_error_count,
        "blunder_rate_percentage": blunder_rate,
        "mistake_rate_percentage": mistake_rate,
        "inaccuracy_rate_percentage": inaccuracy_rate,
        "accuracy_percentage": accuracy_rate,
        "pipeline_failures_total": total_failures,
        "analysis_duration_seconds": total_duration,
        "total_cp_loss": total_cp_loss_all_games,
        "avg_cp_loss_per_game": avg_cp_loss_per_game,
        "avg_cp_loss_per_move": avg_cp_loss_per_move,
    })


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