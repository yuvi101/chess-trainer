import requests
import os
from io import StringIO


USERNAME = os.getenv("LICHESS_USERNAME")
if not USERNAME:
    raise RuntimeError("LICHESS_USERNAME environment variable is not set")
MAX_GAMES = 20

OUTPUT_DIR = "../data/raw_games"
os.makedirs(OUTPUT_DIR, exist_ok=True)

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

response = requests.get(url, params=params, headers=headers)
response.raise_for_status()

games = response.text.strip().split("\n")
print(games)

for idx, game_json in enumerate(games):
    print(idx)
    filename = os.path.join(OUTPUT_DIR, f"game_{idx}.json")
    with open(filename, "w") as f:
        f.write(game_json)
        print(game_json)

print(f"Saved {len(games)} games to {OUTPUT_DIR}")