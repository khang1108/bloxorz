#!/usr/bin/env python3
"""Run automated benchmarks across algorithms on a seeded sample of stages.

Records the core metrics required by the AI project specification:
  - Search time (execution time in milliseconds)
  - Memory usage (peak memory in KiB via tracemalloc)
  - Number of expanded nodes
  - Solution length (number of physical moves)
  - Solution cost and state space exploration details
"""

import csv
import json
import random
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from bloxorz.core.level_loader import LevelLoader
from bloxorz.solvers import BFSSolver, DFSSolver, UCSSolver, AstarSolver


def get_stage_features(board) -> List[str]:
    """Inspects a board to identify structural features."""
    features = []
    from bloxorz.core.constants import TileType
    tile_types = set(board.base_tiles.values())
    if TileType.FRAGILE in tile_types:
        features.append("Fragile")
    if board.switches:
        features.append("Switches")
    if board.bridges:
        features.append("Bridges")
    if board.teleports:
        features.append("Split/Teleport")
    if not features:
        features.append("Standard")
    return features


def run_benchmark(sample_size: int = 10, seed: int = 42) -> List[Dict[str, Any]]:
    levels_dir = REPO_ROOT / "bloxorz" / "levels"
    all_stage_files = sorted(list(levels_dir.glob("stage_*.json")), key=lambda p: p.stem)
    
    random.seed(seed)
    sampled_files = random.sample(all_stage_files, sample_size)
    # Sort sampled files numerically for clean presentation
    sampled_files.sort(key=lambda p: int(p.stem.split("_")[1]) if "_" in p.stem else 0)

    solvers_to_run = [
        ("BFS", BFSSolver),
        ("DFS", DFSSolver),
        ("UCS", UCSSolver),
        ("A*", AstarSolver),
    ]

    print("=" * 80)
    print(f"BLOXZORZ SOLVERS BENCHMARK (Seed: {seed}, Sample Size: {sample_size})")
    print(f"Sampled Stages: {', '.join(p.stem for p in sampled_files)}")
    print("=" * 80)

    results: List[Dict[str, Any]] = []

    for stage_idx, stage_path in enumerate(sampled_files, 1):
        stage_name = stage_path.stem
        board = LevelLoader.load_json_level(stage_path)
        features = get_stage_features(board)
        feature_str = "+".join(features)

        print(f"\n[{stage_idx:02d}/{sample_size:02d}] Evaluating {stage_name} (Features: {feature_str})...")

        for algo_name, SolverCls in solvers_to_run:
            solver = SolverCls()
            start_wall = time.perf_counter()
            res = solver.solve(board.clone())
            elapsed_wall_ms = (time.perf_counter() - start_wall) * 1000.0

            # Consolidate recorded metrics
            search_time_ms = round(res.execution_time_ms if res.execution_time_ms > 0 else elapsed_wall_ms, 3)
            peak_memory_kib = round(float(res.peak_memory_kb), 2)
            expanded = int(res.expanded_nodes)
            moves_count = int(res.solution_length)
            is_solved = bool(res.is_solved)
            visited = int(res.visited_count)
            cost = round(float(res.solution_cost), 2) if res.solution_cost is not None else None
            max_depth = int(res.max_depth)

            # Move sequence representation
            moves_str = " ".join(
                getattr(a, "name", str(a)) for a in res.moves
            )

            record = {
                "stage": stage_name,
                "stage_number": int(stage_name.split("_")[1]) if "_" in stage_name else 0,
                "features": feature_str,
                "algorithm": algo_name,
                "is_solved": is_solved,
                "search_time_ms": search_time_ms,
                "peak_memory_kib": peak_memory_kib,
                "expanded_nodes": expanded,
                "solution_length": moves_count,
                "solution_cost": cost,
                "visited_count": visited,
                "max_depth": max_depth,
                "moves": moves_str,
            }
            results.append(record)

            print(
                f"  -> {algo_name:5s}: Solved={str(is_solved):5s} | "
                f"Moves={moves_count:3d} | "
                f"Time={search_time_ms:9.2f} ms | "
                f"PeakMem={peak_memory_kib:9.2f} KiB | "
                f"Expanded={expanded:6d} | "
                f"Cost={str(cost):>5s}"
            )

    return results


def save_results(results: List[Dict[str, Any]]) -> None:
    data_dir = REPO_ROOT / "data"
    data_dir.mkdir(exist_ok=True)

    json_path = data_dir / "benchmark_results.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n[OK] Results saved to JSON: {json_path}")

    csv_path = data_dir / "benchmark_results.csv"
    if results:
        fieldnames = list(results[0].keys())
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)
    print(f"[OK] Results saved to CSV:  {csv_path}")


def main() -> None:
    results = run_benchmark(sample_size=10, seed=42)
    save_results(results)


if __name__ == "__main__":
    main()

