from report_generator import aggregate_stats, build_prompt


def make_row(lichess_id="g1", opening="Sicilian Defense", color="white", result="white",
             move_number=1, move_played="e4", best_move="e4", cp_loss=0,
             label="Good", moves="e4 e5", opponent="bob"):
    """Matches the column order of fetch_weekly_data()'s SELECT."""
    return (lichess_id, opening, color, result, move_number, move_played,
            best_move, cp_loss, label, moves, opponent)


def test_aggregate_stats_good_moves_use_label_not_zero_cp_loss():
    rows = [
        make_row(move_number=1, cp_loss=0, label="Good"),
        make_row(move_number=2, cp_loss=30, label="Good"),  # <50cp but not exactly 0
    ]
    stats = aggregate_stats(rows)
    assert len(stats["games"]["g1"]["good_moves"]) == 2


def test_aggregate_stats_avg_cp_loss_is_plain_average_of_per_move_deltas():
    rows = [
        make_row(move_number=1, cp_loss=10, label="Good"),
        make_row(move_number=2, cp_loss=20, label="Inaccuracy"),
    ]
    stats = aggregate_stats(rows)
    assert stats["avg_cp_loss"] == 15.0


def test_aggregate_stats_per_game_total_cp_loss_sums_deltas():
    rows = [
        make_row(move_number=1, cp_loss=10, label="Good"),
        make_row(move_number=2, cp_loss=20, label="Inaccuracy"),
    ]
    stats = aggregate_stats(rows)
    assert stats["games"]["g1"]["total_cp_loss"] == 30


def test_build_prompt_includes_game_and_opening_details():
    rows = [make_row()]
    stats = aggregate_stats(rows)
    prompt = build_prompt(stats)
    assert "vs bob" in prompt
    assert "Sicilian Defense" in prompt


def test_build_prompt_good_move_details_show_actual_cp_loss():
    rows = [make_row(move_number=1, cp_loss=30, label="Good")]
    stats = aggregate_stats(rows)
    prompt = build_prompt(stats)
    assert "CP loss: 30" in prompt
    assert "perfect move" not in prompt
