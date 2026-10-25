"""Generate CSV statistics and plots for BFS searches across all stages."""

import argparse
import csv
import sys
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Callable, List, Tuple

import matplotlib.pyplot as plt

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if __package__ in (None, "") and str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from bloxorz.core.level_loader import load_level_from_file  # noqa: E402
from bloxorz.solvers.bfs import BFSSolver, BFSSolverResult  # noqa: E402


@dataclass(frozen=True)
class StageStatistics:
    stage_number: int
    summary: str
    result: BFSSolverResult


CSV_FIELDS = (
    "Stage",
    "Summary",
    "Solved",
    "Moves Length",
    "Visited States",
    "Depth",
    "Search Time (ms)",
    "Peak Memory (bytes)",
    "Peak Memory (KiB)",
    "Expanded Nodes",
)


def _stage_number(stage_file: Path) -> int:
    try:
        return int(stage_file.stem.removeprefix("stage_"))
    except ValueError as exc:
        raise ValueError(f"Invalid stage filename: {stage_file.name}") from exc


def _collect_statistics(levels_dir: Path) -> List[StageStatistics]:
    stage_files = sorted(
        levels_dir.glob("stage_*.json"),
        key=lambda path: _stage_number(path),
    )
    if not stage_files:
        raise FileNotFoundError(f"No stage_*.json files found in {levels_dir}")

    solver = BFSSolver()
    statistics = []
    for stage_file in stage_files:
        board = load_level_from_file(stage_file)
        result = solver.solve(board)
        if not isinstance(result, BFSSolverResult):
            raise TypeError(f"BFS returned an unexpected result for {stage_file.name}")
        statistics.append(
            StageStatistics(
                stage_number=_stage_number(stage_file),
                summary=result.summary(),
                result=result,
            )
        )
    return statistics


def _write_csv(statistics: List[StageStatistics], csv_path: Path) -> None:
    with csv_path.open("w", newline="", encoding="utf-8") as report_file:
        writer = csv.DictWriter(report_file, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for stage in statistics:
            result = stage.result
            writer.writerow(
                {
                    "Stage": stage.stage_number,
                    "Summary": stage.summary,
                    "Solved": result.is_solved,
                    "Moves Length": len(result.moves),
                    "Visited States": result.visited_count,
                    "Depth": result.max_depth,
                    "Search Time (ms)": result.execution_time_ms,
                    "Peak Memory (bytes)": result.peak_memory_bytes,
                    "Peak Memory (KiB)": result.peak_memory_bytes / 1024,
                    "Expanded Nodes": result.expanded_nodes,
                }
            )

        writer.writerow(
            {
                "Stage": "Average",
                "Moves Length": mean(len(item.result.moves) for item in statistics),
                "Visited States": mean(item.result.visited_count for item in statistics),
                "Depth": mean(item.result.max_depth for item in statistics),
                "Search Time (ms)": mean(
                    item.result.execution_time_ms for item in statistics
                ),
                "Peak Memory (bytes)": mean(
                    item.result.peak_memory_bytes for item in statistics
                ),
                "Peak Memory (KiB)": mean(
                    item.result.peak_memory_bytes / 1024 for item in statistics
                ),
                "Expanded Nodes": mean(
                    item.result.expanded_nodes for item in statistics
                ),
            }
        )


def _plot_metric(
    statistics: List[StageStatistics],
    output_path: Path,
    title: str,
    ylabel: str,
    value_getter: Callable[[BFSSolverResult], float],
) -> None:
    stages = [item.stage_number for item in statistics]
    values = [value_getter(item.result) for item in statistics]

    figure, axis = plt.subplots(figsize=(10, 6))
    axis.plot(stages, values, marker="o")
    axis.set_title(title)
    axis.set_xlabel("Stage Number")
    axis.set_ylabel(ylabel)
    axis.set_xticks(stages)
    axis.grid(True, linestyle="--", alpha=0.5)
    figure.tight_layout()
    figure.savefig(output_path, dpi=150)
    plt.close(figure)


def generate_bfs_report(
    levels_dir: Path | None = None,
    output_dir: Path | None = None,
) -> Tuple[Path, Path, Path]:
    """Run BFS on each stage and create its CSV report and two plots."""
    stages_path = levels_dir or PROJECT_ROOT / "bloxorz" / "levels"
    reports_path = output_dir or PROJECT_ROOT / "docs" / "algo" / "bfs"
    reports_path.mkdir(parents=True, exist_ok=True)

    statistics = _collect_statistics(stages_path)
    csv_path = reports_path / "bfs_stage_statistics.csv"
    search_time_plot = reports_path / "bfs_search_time.png"
    peak_memory_plot = reports_path / "bfs_peak_memory.png"

    _write_csv(statistics, csv_path)
    _plot_metric(
        statistics,
        search_time_plot,
        "BFS Search Time by Stage",
        "Search Time (ms)",
        lambda result: result.execution_time_ms,
    )
    _plot_metric(
        statistics,
        peak_memory_plot,
        "BFS Peak Memory by Stage",
        "Peak Memory (KiB)",
        lambda result: result.peak_memory_bytes / 1024,
    )
    return csv_path, search_time_plot, peak_memory_plot


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate BFS statistics and plots for every stage."
    )
    parser.add_argument(
        "--levels-dir",
        type=Path,
        help="Directory containing stage_*.json files (defaults to bloxorz/levels).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Directory for the CSV and plot files (defaults to docs/algo/bfs).",
    )
    arguments = parser.parse_args()

    csv_path, search_time_plot, peak_memory_plot = generate_bfs_report(
        arguments.levels_dir,
        arguments.output_dir,
    )
    print(f"CSV report: {csv_path}")
    print(f"Search-time plot: {search_time_plot}")
    print(f"Peak-memory plot: {peak_memory_plot}")


if __name__ == "__main__":
    main()
