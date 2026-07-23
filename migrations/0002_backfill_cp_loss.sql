-- engine/analyze_game.py used to store a running cumulative cp_loss per move
-- instead of the per-move delta. This recovers the true per-move delta from
-- the cumulative values already in the table: delta_i = cum_i - cum_(i-1),
-- with cum_0 treated as 0 for each game's first analyzed move.
WITH deltas AS (
    SELECT
        id,
        cp_loss - COALESCE(
            LAG(cp_loss) OVER (PARTITION BY game_id ORDER BY move_number, id),
            0
        ) AS delta
    FROM moves
)
UPDATE moves m
SET cp_loss = deltas.delta
FROM deltas
WHERE m.id = deltas.id;
