import csv
from pathlib import Path

import pytest

from bloxorz.solvers.benchmark_bfs import generate_bfs_report


def test_generate_bfs_report_writes_stage_summaries_averages_and_plots(tmp_path):
    project_root = Path(__file__).parent.parent
    levels_dir = tmp_path / "levels"
    levels_dir.mkdir()
    (levels_dir / "stage_04.json").write_text(
        (project_root / "bloxorz" / "levels" / "stage_04.json").read_text(
            encoding="utf-8"
        ),
        encoding="utf-8",
    )
    output_dir = tmp_path / "report"

    csv_path, search_time_plot, peak_memory_plot = generate_bfs_report(
        levels_dir,
        output_dir,
    )

    with csv_path.open(newline="", encoding="utf-8") as report_file:
        rows = list(csv.DictReader(report_file))

    assert len(rows) == 2
    stage_row, average_row = rows
    assert stage_row["Stage"] == "4"
    assert stage_row["Summary"].startswith("[SOLVED]")
    assert "Search Time:" in stage_row["Summary"]
    assert "Peak Memory:" in stage_row["Summary"]
    assert "Expanded Nodes:" in stage_row["Summary"]
    assert float(average_row["Moves Length"]) == float(stage_row["Moves Length"])
    assert float(average_row["Visited States"]) == float(stage_row["Visited States"])
    assert float(average_row["Depth"]) == float(stage_row["Depth"])
    assert float(average_row["Search Time (ms)"]) == float(
        stage_row["Search Time (ms)"]
    )
    assert float(average_row["Peak Memory (bytes)"]) == float(
        stage_row["Peak Memory (bytes)"]
    )
    assert float(average_row["Expanded Nodes"]) == float(
        stage_row["Expanded Nodes"]
    )
    assert search_time_plot.is_file()
    assert peak_memory_plot.is_file()


def test_generate_bfs_report_rejects_empty_levels_directory(tmp_path):
    levels_dir = tmp_path / "empty_levels"
    levels_dir.mkdir()

    with pytest.raises(FileNotFoundError, match="No stage_\\*\\.json files found"):
        generate_bfs_report(levels_dir, tmp_path / "report")
