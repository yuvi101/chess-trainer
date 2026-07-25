from llm_client import _calculate_claude_cost


def test_calculate_claude_cost_zero_tokens():
    assert _calculate_claude_cost(0, 0) == 0


def test_calculate_claude_cost_matches_per_million_pricing():
    # $3 / M input tokens, $15 / M output tokens
    cost = _calculate_claude_cost(input_tokens=1_000_000, output_tokens=1_000_000)
    assert cost == 18.0


def test_calculate_claude_cost_input_only():
    cost = _calculate_claude_cost(input_tokens=1_000_000, output_tokens=0)
    assert cost == 3.0
