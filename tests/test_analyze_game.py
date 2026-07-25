from analyze_game import classify_move, compute_cp_loss


def test_classify_move_good():
    assert classify_move(0) == "Good"
    assert classify_move(49) == "Good"


def test_classify_move_inaccuracy():
    assert classify_move(50) == "Inaccuracy"
    assert classify_move(149) == "Inaccuracy"


def test_classify_move_mistake():
    assert classify_move(150) == "Mistake"
    assert classify_move(299) == "Mistake"


def test_classify_move_blunder():
    assert classify_move(300) == "Blunder"
    assert classify_move(1000) == "Blunder"


def test_compute_cp_loss_positive_difference():
    assert compute_cp_loss(best_score=100, after_score=50) == 50


def test_compute_cp_loss_clamped_to_zero_when_position_improves():
    assert compute_cp_loss(best_score=50, after_score=100) == 0


def test_compute_cp_loss_equal_scores():
    assert compute_cp_loss(best_score=100, after_score=100) == 0
