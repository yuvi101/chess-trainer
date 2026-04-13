import requests
import os
#from io import StringIO
from shared.db import get_connection
import json
import logging



USERNAME = os.getenv("LICHESS_USERNAME")
if not USERNAME:
    raise RuntimeError("LICHESS_USERNAME environment variable is not set")
MAX_GAMES = 20

# OUTPUT_DIR = "../data/raw_games"
# os.makedirs(OUTPUT_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)


url = f"https://lichess.org/api/games/user/{USERNAME}"
params = {
    "max": MAX_GAMES,
    "pgnInJson": True,
    "opening": True,
    "moves": True
}

headers = {
    "Accept": "application/x-ndjson"
}


def save_game_to_db(game):
    conn = get_connection()
    cur = conn.cursor()
    try:
        # Determine opponent name
        white_name = game["players"]["white"]["user"]["name"]
        black_name = game["players"]["black"]["user"]["name"]

        my_color = "white" if white_name == USERNAME else "black"
        opponent = black_name if white_name == USERNAME else white_name

        cur.execute("""
            INSERT INTO games (lichess_id, played_at, opening, color, result, time_control, moves, opponent)
            VALUES (%s, to_timestamp(%s / 1000.0), %s, %s, %s, %s, %s, %s)
        """, (
            game["id"],
            game.get("createdAt"),
            game.get("opening", {}).get("name"),
            my_color,
            # "white" if game["players"]["white"]["user"]["name"] == USERNAME else "black",
            game.get("winner", "draw"),
            str(game.get("clock", {}).get("initial")),
            game.get("moves", ""),
            opponent
        ))
        conn.commit()
        logging.info(f"Saved game {game['id']} to DB — you played {my_color} vs {opponent}")
    except Exception as e:
        conn.rollback()
        logging.error(f"Failed to save game {game['id']}: {e}")
    finally:
        cur.close()
        conn.close()

def fetch_games():
    response = requests.get(url, params=params, headers=headers)
    response.raise_for_status()

    games = response.text.strip().split("\n")
    logging.info(f"Fetched {len(games)} games from Lichess")
    return games

def main():
    games = fetch_games()
    for game_str in games:
        game = json.loads(game_str)  # parse each line into a dict
        save_game_to_db(game)
    logging.info(f"Processed {len(games)} games.")

if __name__ == "__main__":
    main()