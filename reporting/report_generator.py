import os
import logging
from datetime import datetime
import chess
import chess.svg
import re
from shared.db import get_connection
from llm_client import call_llm

# ---------- Logging ----------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)


# ---------- Step 1: Fetch data ----------
def fetch_weekly_data():
    """Fetch all games and moves from the past 7 days."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT
            g.lichess_id,
            g.opening,
            g.color,
            g.result,
            m.move_number,
            m.move_played,
            m.best_move,
            m.cp_loss,
            m.label,
            g.moves,
            g.opponent
        FROM games g
        JOIN moves m ON m.game_id = g.id
        WHERE g.played_at >= NOW() - INTERVAL '999 days'
        ORDER BY g.played_at DESC, m.move_number ASC
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


# ---------- Step 2: Aggregate stats ----------
def aggregate_stats(rows):
    """Turn raw rows into structured stats for the prompt."""
    total_moves = len(rows)
    blunders = [r for r in rows if r[8] == "Blunder"]
    mistakes = [r for r in rows if r[8] == "Mistake"]
    inaccuracies = [r for r in rows if r[8] == "Inaccuracy"]
    good_moves = [r for r in rows if r[8] == "Good"]

    games = {}
    game_counter = 1
    for row in rows:
        lichess_id = row[0]
        cp_loss = row[7]
        opponent = row[10]
        if lichess_id not in games:
            games[lichess_id] = {
                "lichess_id": lichess_id,
                "opening": row[1],
                "color": row[2],
                "result": row[3],
                "moves": row[9],
                "opponent": opponent,
                "game_number": game_counter,
                "total_cp_loss": 0,
                "blunders": [],
                "good_moves": [],
            }
        games[lichess_id]["total_cp_loss"] += cp_loss
        if row[8] == "Blunder":
            games[lichess_id]["blunders"].append(row)
        if row[8] == "Good" and cp_loss == 0:
            games[lichess_id]["good_moves"].append(row)

    avg_cp_loss = sum(r[7] for r in rows) / total_moves if total_moves > 0 else 0

    return {
        "total_moves": total_moves,
        "total_games": len(games),
        "avg_cp_loss": round(avg_cp_loss, 1),
        "blunders": blunders,
        "mistakes": mistakes,
        "inaccuracies": inaccuracies,
        "good_moves": good_moves,
        "games": games,
    }


# ---------- Step 3: Render blunder boards ----------
# def render_blunder_boards(stats):
#     """
#     For each blunder, replay the game up to that move
#     and render the board as SVG.
#     Returns a dict: { (lichess_id, move_number): svg_string }
#     """
#     boards = {}

#     for game in stats["games"].values():
#         if not game["blunders"]:
#             continue

#         moves_str = game["moves"]
#         if not moves_str:
#             continue

#         all_moves = moves_str.split()
#         board = chess.Board()

#         for i, move in enumerate(all_moves):
#             move_number = (i // 2) + 1

#             is_blunder = any(
#                 b[4] == move_number and b[5] == move
#                 for b in game["blunders"]
#             )

#             try:
#                 board.push_san(move)
#             except Exception:
#                 break

#             if is_blunder:
#                 svg = chess.svg.board(
#                     board,
#                     size=350,
#                     lastmove=board.peek(),
#                     colors={
#                         "square light": "#f0d9b5",
#                         "square dark": "#b58863"
#                     }
#                 )
#                 boards[(game["lichess_id"], move_number)] = svg

#     return boards

def render_move_boards(stats):
    """
    Render board SVGs for all significant moves (blunders, mistakes, good moves).
    Returns dict: { (lichess_id, move_number): svg_string }
    """
    boards = {}
    significant_labels = {"Blunder", "Mistake", "Good"}

    for game in stats["games"].values():
        moves_str = game["moves"]
        if not moves_str:
            continue

        all_moves = moves_str.split()
        board = chess.Board()

        # Build a set of significant move numbers for this game
        significant_moves = set()
        for row in game["blunders"] + game["good_moves"]:
            significant_moves.add(row[4])  # move_number

        for i, move in enumerate(all_moves):
            move_number = (i // 2) + 1
            try:
                board.push_san(move)
            except Exception:
                break

            if move_number in significant_moves:
                svg = chess.svg.board(
                    board,
                    size=350,
                    lastmove=board.peek(),
                    colors={
                        "square light": "#f0d9b5",
                        "square dark": "#b58863"
                    }
                )
                boards[(game["lichess_id"], move_number)] = svg

    return boards


# ---------- Step 4: Build prompt ----------
def build_prompt(stats):
    game_reference = ""
    for game in stats["games"].values():
        game_reference += (
            f"- Game {game['game_number']}: vs {game['opponent']} "
            f"(you played as {game['color']}, "
            f"(ID: {game['lichess_id']}, opening: {game['opening'] or 'Unknown'}, "
            f"result: {game['result']}, you played as {game['color']})\n"
        )

    blunder_details = ""
    for b in stats["blunders"][:10]:
        lichess_id = b[0]
        game = stats["games"][lichess_id]
        #game_label = f"Game {game['game_number']} (vs {game['opponent']})"
        blunder_details += (
            f"- Game {b[0]}, Move {b[4]}: played {b[5]} "
            f"(best was {b[6]}, CP loss: {b[7]})\n"
        )

    good_move_details = ""
    for g in stats["good_moves"][:5]:
        lichess_id = g[0]
        game = stats["games"][lichess_id]
        #game_label = f"Game {game['game_number']} (vs {game['opponent']})"
        good_move_details += (
            f"- Game {g[0]}, Move {g[4]}: {g[5]} (0 CP loss, perfect move)\n"
        )

    opening_summary = {}
    for game in stats["games"].values():
        op = game["opening"] or "Unknown"
        if op not in opening_summary:
            opening_summary[op] = {"games": 0, "wins": 0, "total_cp_loss": 0}
        opening_summary[op]["games"] += 1
        opening_summary[op]["total_cp_loss"] += game["total_cp_loss"]
        if game["result"] == "white" and game["color"] == "white":
            opening_summary[op]["wins"] += 1
        elif game["result"] == "black" and game["color"] == "black":
            opening_summary[op]["wins"] += 1

    opening_details = ""
    for op, data in opening_summary.items():
        opening_details += (
            f"- {op}: {data['games']} games, "
            f"{data['wins']} wins, "
            f"avg CP loss {round(data['total_cp_loss'] / data['games'], 1)}\n"
        )

    prompt = f"""
You are an expert chess coach writing a weekly coaching report for your student.
Be specific, encouraging but honest, and actionable. Write as if you are their
personal tutor sending them a message after reviewing their games this week.

IMPORTANT FORMATTING INSTRUCTION:
- Refer to games as "Game 1 (vs Opponent)" not by their ID, for example:
    Game 1 (vs Opponent_1_name) or Game 5 (vs Another_opponent_name).
- Make sure to take the names of the opponents from the game data, as well as the game numbers.
    Look for the keys "opponent" and "game_number" in the game data. Also point out what color I was playing.
- Example: Game 1 (vs Opponent_1_name) - you played as white.
- When you discuss a specific move, insert the board tag that is provided 
  in square brackets next to each move on its own line
- The board tags look like {{BOARD:id:move}} and will be replaced with 
  actual board diagrams in the final report

Here is their data from this week:

OVERALL STATS:
- Games played: {stats['total_games']}
- Total moves analyzed: {stats['total_moves']}
- Average CP loss per move: {stats['avg_cp_loss']}
- Blunders: {len(stats['blunders'])}
- Mistakes: {len(stats['mistakes'])}
- Inaccuracies: {len(stats['inaccuracies'])}
- Good moves: {len(stats['good_moves'])}

GAME REFERENCE (use these friendly names when discussing games):
{game_reference}

BLUNDERS THIS WEEK:
{blunder_details}

GOOD MOVES THIS WEEK:
{good_move_details}

OPENINGS PLAYED:
{opening_details}

Please write a detailed coaching report that includes:
1. Overall performance summary
2. Analysis of each blunder — what went wrong and what should have been played,
   include the board tag provided for each move on its own line
3. Patterns you notice across multiple games
4. Praise for good moves
5. Opening recommendations based on their results
6. A specific training plan for next week with 3-5 actionable items

Write in a warm, personal, encouraging tone like a real coach would.
"""
    return prompt


# ---------- Step 5: Save report to DB ----------
def save_report_to_db(report):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO llm_reports (generated_at, content, tokens_used, cost_usd, latency_ms)
            VALUES (NOW(), %s, %s, %s, %s)
        """, (
            report["content"],
            report["tokens_used"],
            report["cost_usd"],
            report["latency_ms"],
        ))
        conn.commit()
        logging.info(
            f"Report saved — "
            f"provider: {report['provider']} | "
            f"tokens: {report['tokens_used']} | "
            f"cost: ${report['cost_usd']:.4f} | "
            f"latency: {report['latency_ms']}ms"
        )
    except Exception as e:
        conn.rollback()
        logging.error(f"Failed to save report: {e}")
    finally:
        cur.close()
        conn.close()


# ---------- Step 6: Generate HTML ----------
def generate_html_report(report_text, boards, stats):
    # boards_html = ""
    # for (lichess_id, move_number), svg in boards.items():
    #     boards_html += f"""
    #     <div class="board-section">
    #         <h3>Game {lichess_id} — Move {move_number} (Blunder)</h3>
    #         <div class="board">{svg}</div>
    #     </div>
    #     """
    def replace_board_tag(match):
        lichess_id = match.group(1)
        move_number = int(match.group(2))
        key = (lichess_id, move_number)

        # Look up opponent and game number
        game = stats["games"].get(lichess_id, {})
        opponent = game.get("opponent", lichess_id)  # fallback to ID if not found
        game_number = game.get("game_number", "?")

        if key in boards:
            svg = boards[key]
            return f"""
            <div class="board-inline">
                <div class="board">{svg}</div>
                <p class="board-caption">Position after move {move_number}</p>
            </div>
            """
        return ""  # if board not found, just remove the tag

    # Replace {BOARD:id:move} tags with actual SVG boards
    report_with_boards = re.sub(
        r'\{BOARD:([^:]+):(\d+)\}',
        replace_board_tag,
        report_text
    )

    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Weekly Chess Coaching Report</title>
    <style>
        body {{
            font-family: Georgia, serif;
            max-width: 900px;
            margin: 40px auto;
            padding: 20px;
            background: #fafafa;
            color: #222;
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 2px solid #2c3e50;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #2c3e50;
            margin-top: 40px;
        }}
        .report-text {{
            white-space: pre-wrap;
            line-height: 1.8;
            font-size: 1.05em;
        }}
        .board-inline {{
            margin: 20px auto;
            padding: 15px;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            text-align: center;
            max-width: 400px;
        }}
        .board-caption {{
            color: #888;
            font-size: 0.85em;
            margin-top: 8px;
        }}
        .date {{
            color: #888;
            font-size: 0.9em;
            margin-bottom: 30px;
        }}
    </style>
</head>
<body>
    <h1>♟️ Weekly Chess Coaching Report</h1>
    <p class="date">Generated on {datetime.now().strftime("%B %d, %Y")}</p>
    <div class="report-text">{report_with_boards}</div> 

</body>
</html>
"""
    return html


# ---------- Main ----------
def main():
    os.makedirs("/app/reports", exist_ok=True)

    logging.info("Fetching weekly data...")
    rows = fetch_weekly_data()

    if not rows:
        logging.info("No data found.")
        return

    logging.info(f"Aggregating stats for {len(rows)} moves...")
    stats = aggregate_stats(rows)

    logging.info("Rendering blunder boards...")
    #boards = render_blunder_boards(stats)
    boards = render_move_boards(stats)

    logging.info("Calling LLM for coaching report...")
    prompt = build_prompt(stats)
    report = call_llm(prompt)

    logging.info("Saving report to DB...")
    save_report_to_db(report)

    logging.info("Generating HTML report...")
    html = generate_html_report(report["content"], boards, stats)

    report_path = f"/app/reports/report_{datetime.now().strftime('%Y%m%d')}.html"
    with open(report_path, "w") as f:
        f.write(html)

    logging.info(f"Report saved to {report_path}")


if __name__ == "__main__":
    main()