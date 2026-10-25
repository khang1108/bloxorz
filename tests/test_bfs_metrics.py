from pathlib import Path

from bloxorz.core.level_loader import load_level_from_file
from bloxorz.solvers.bfs import BFSSolver


def test_bfs_records_search_metrics():
    board = load_level_from_file(Path("bloxorz/levels/stage_04.json"))

    result = BFSSolver().solve(board)

    assert result.is_solved
    assert result.execution_time_ms >= 0
    assert result.peak_memory_bytes > 0
    assert result.expanded_nodes > 0
    assert result.visited_count == result.expanded_nodes + 1
    assert "Search Time:" in result.summary()
    assert "Peak Memory:" in result.summary()
    assert "Expanded Nodes:" in result.summary()
