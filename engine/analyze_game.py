import json
from pathlib import Path
import chess
import chess.engine
import os
import logging

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
 

def load_game(path):
    with open(path, "r") as f:
        return json.load(f)


def classify_move(cp_loss):
    if cp_loss < 50:
        return "Good"
    elif cp_loss < 150:
        return "Inaccuracy"
    elif cp_loss < 300:
        return "Mistake"
    else:
        return "Blunder"


def analyze_game(game_json, output_file, engine):
    board = chess.Board()
    moves = game_json["moves"].split()
    if not moves:
        logging.warning(f"Skipping game with no moves: {output_file.name}")
        return None

    username = USERNAME
    white_player = game_json["players"]["white"]["user"]["name"]
    my_color = chess.WHITE if username == white_player else chess.BLACK

    results = []
    total_cp_loss = 0
    total_blunders = 0

    for i, move in enumerate(moves):

        # Only analyze BEFORE your move
        if board.turn == my_color:
            info_before = engine.analyse(board, chess.engine.Limit(depth=15))
            best_move = info_before["pv"][0]
            # before move
            best_score = info_before["score"].pov(my_color).score(mate_score=10000)
            
            # Convert best move to SAN on the current board BEFORE playing your move
            best_move_san = board.san(best_move)

            # Play your move
            try:
                board.push_san(move)
            except Exception as e:
                logging.error(f"Illegal move {move} in {output_file.name}: {e}")
                break

            info_after = engine.analyse(board, chess.engine.Limit(depth=15))
            # after move  
            after_score = info_after["score"].pov(my_color).score(mate_score=10000)

            #cp_loss = best_score - after_score
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
            # Opponent move — just play it
            board.push_san(move)

    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)

    return {
    "total_cp_loss": total_cp_loss,
    "total_blunders": total_blunders,
    "moves_analyzed": len(results)
    }



def analyze_all_games():
    with chess.engine.SimpleEngine.popen_uci(ENGINE_CMD) as engine:
        for game_file in RAW_GAMES_DIR.glob("*.json"):
            analysis_file = RESULTS_DIR / f"{game_file.stem}_analysis.json"
            
            # skip already analyzed games
            if analysis_file.exists():
                logging.info(f"Skipping already analyzed game: {game_file.name}")
                continue
            else:
                game = load_game(game_file)
                logging.info(f"Analyzing {game_file.name} ...")
                r = analyze_game(game, analysis_file, engine)
                logging.info(f"Done analyzing {game_file.name}")
                logging.info(
                    f"CP Loss: {r['total_cp_loss']} | "
                    f"Blunders: {r['total_blunders']} | "
                    f"Moves analyzed: {r['moves_analyzed']}"
                )

def wait_for_engine(retries=5, delay=2):
    """Try to connect to Stockfish over TCP before starting analysis."""
    import socket
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