import json
from pathlib import Path
import chess
import chess.engine
import os


# ------------------- CONFIG ----------------------
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_GAMES_DIR = DATA_DIR / "raw_games"
RESULTS_DIR = DATA_DIR / "engine_results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
USERNAME = os.getenv("LICHESS_USERNAME")

# ---------- Connect to Stockfish over TCP ----------
ENGINE_CMD = ["nc", "stockfish_engine", "3334"]


def load_game(path):
    with open(path, "r") as f:
        return json.load(f)


def get_score(info):
    """Normalize engine score to centipawns from White's perspective."""
    return info["score"].white().score(mate_score=10000)


def classify_move(cp_loss):
    if cp_loss < 50:
        return "Good"
    elif cp_loss < 150:
        return "Inaccuracy"
    elif cp_loss < 300:
        return "Mistake"
    else:
        return "Blunder"


def analyze_game(game_json, output_file):
    board = chess.Board()
    moves = game_json["moves"].split()

    username = USERNAME
    white_player = game_json["players"]["white"]["user"]["name"]
    my_color = chess.WHITE if username == white_player else chess.BLACK

    results = []
    total_cp_loss = 0
    total_blunders = 0

    with chess.engine.SimpleEngine.popen_uci(ENGINE_CMD) as engine:
        for i, move in enumerate(moves):

            # Only analyze BEFORE your move
            if board.turn == my_color:
                info_before = engine.analyse(board, chess.engine.Limit(depth=15))
                best_move = info_before["pv"][0]
                best_score = get_score(info_before)
                
                # Convert best move to SAN on the current board BEFORE playing your move
                best_move_san = board.san(best_move)

                # Play your move
                board.push_san(move)

                info_after = engine.analyse(board, chess.engine.Limit(depth=15))
                after_score = get_score(info_after)

                cp_loss = best_score - after_score
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



def ananlyze_all_games():
    for game_file in RAW_GAMES_DIR.glob("*.json"):
        analysis_file = RESULTS_DIR / f"{game_file.stem}_analysis.json"
        
        print("THIS IS THE JSON FILE:")
        print(game_file.name)
        # skip already analyzed games
        if analysis_file.exists():
            print(f"Skipping already analyzed game: {game_file.name}")
            continue
        else:
            game = load_game(game_file)
            r = analyze_game(game, analysis_file)
            print(f"Analyzing {game_file.name} ...")
            print(
                f"CP Loss: {r['total_cp_loss']} | "
                f"Blunders: {r['total_blunders']} | "
                f"Moves analyzed: {r['moves_analyzed']}"
            )
                        

def main():
    ananlyze_all_games()
    

if __name__ == "__main__":
    main()