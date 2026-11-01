#!/usr/bin/env python3
"""Ablation Study Experiment Runner for Bloxorz A* Heuristic Components.

Systematically evaluates 6 heuristic variants across 10 benchmark stages:
  - H0 (Null Heuristic / UCS Baseline): h(n) = 0
  - H1 (Standard Unrelaxed Manhattan): h(n) = min Manhattan distance (non-admissible, h > h*)
  - H2 (Relaxed Manhattan Only): h(n) = ceil(min Manhattan / 2.0) (admissible baseline)
  - H3 (Relaxed Manhattan + Orientation Penalty): adds h_orient = 2 if on goal but lying down
  - H4 (Full Proposed Heuristic): H3 + h_merge = max(0, dist_between_cubes - 1) for split cubes
  - H5 (True-Distance Heuristic - SoCS 2009 / Sturtevant et al.): Precomputed backward BFS on relaxed grid

Outputs results to data/ablation_results.json and data/ablation_results.csv.
"""

import csv
import json
import math
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from bloxorz.core.block import BaseBlockState, SplitBlockState
from bloxorz.core.board import Board
from bloxorz.core.constants import BlockOrientation
from bloxorz.core.level_loader import LevelLoader
from bloxorz.solvers.astar import AstarSolver
from bloxorz.solvers.heuristics import TrueDistanceHeuristic


# --- HEURISTIC COMPONENT DEFINITIONS ---

def h0_null(block: BaseBlockState, board: Board) -> float:
    """H0: Null heuristic (equivalent to UCS / Dijkstra)."""
    return 0.0


def h1_unrelaxed_manhattan(block: BaseBlockState, board: Board) -> float:
    """H1: Standard unrelaxed Manhattan distance (non-admissible, h > h*)."""
    gx, gy = board.goal_pos
    if isinstance(block, SplitBlockState):
        c1 = block.cube1 if hasattr(block, "cube1") else (block.b1.x, block.b1.y)
        c2 = block.cube2 if hasattr(block, "cube2") else (block.b2.x, block.b2.y)
        d1 = abs(c1[0] - gx) + abs(c1[1] - gy)
        d2 = abs(c2[0] - gx) + abs(c2[1] - gy)
        return float(min(d1, d2))
    occ = block.occupied_cells
    if not occ:
        return 0.0
    return float(min(abs(x - gx) + abs(y - gy) for x, y in occ))


def h2_relaxed_manhattan_only(block: BaseBlockState, board: Board) -> float:
    """H2: Relaxed Manhattan distance only (admissible baseline, no orient, no merge)."""
    gx, gy = board.goal_pos
    if isinstance(block, SplitBlockState):
        c1 = block.cube1 if hasattr(block, "cube1") else (block.b1.x, block.b1.y)
        c2 = block.cube2 if hasattr(block, "cube2") else (block.b2.x, block.b2.y)
        d1 = abs(c1[0] - gx) + abs(c1[1] - gy)
        d2 = abs(c2[0] - gx) + abs(c2[1] - gy)
        return float(math.ceil(min(d1, d2) / 2.0))
    occ = block.occupied_cells
    if not occ:
        return 0.0
    return float(math.ceil(min(abs(x - gx) + abs(y - gy) for x, y in occ) / 2.0))


def h3_relaxed_plus_orientation(block: BaseBlockState, board: Board) -> float:
    """H3: Relaxed Manhattan + orientation penalty (no merge cost for split)."""
    gx, gy = board.goal_pos
    if isinstance(block, SplitBlockState):
        c1 = block.cube1 if hasattr(block, "cube1") else (block.b1.x, block.b1.y)
        c2 = block.cube2 if hasattr(block, "cube2") else (block.b2.x, block.b2.y)
        d1 = abs(c1[0] - gx) + abs(c1[1] - gy)
        d2 = abs(c2[0] - gx) + abs(c2[1] - gy)
        return float(math.ceil(min(d1, d2) / 2.0))
    occ = block.occupied_cells
    if not occ:
        return 0.0
    min_d = min(abs(x - gx) + abs(y - gy) for x, y in occ)
    if min_d == 0:
        if getattr(block, "orientation", None) == BlockOrientation.STANDING:
            return 0.0
        return 2.0
    return float(math.ceil(min_d / 2.0))


def h4_full_proposed(block: BaseBlockState, board: Board) -> float:
    """H4: Full proposed heuristic (Relaxed Manhattan + Orientation + Merge cost)."""
    return AstarSolver.heuristic(block, board)


# --- EXPERIMENT HARNESS ---

HEURISTIC_FACTORIES: List[Tuple[str, str, Callable[[Board], Callable[[BaseBlockState, Board], float]], bool]] = [
    ("H0", "Null Heuristic (UCS)", lambda b: h0_null, True),
    ("H1", "Unrelaxed Manhattan (Non-admissible)", lambda b: h1_unrelaxed_manhattan, False),
    ("H2", "Relaxed Manhattan Only", lambda b: h2_relaxed_manhattan_only, True),
    ("H3", "Relaxed + Orientation Penalty", lambda b: h3_relaxed_plus_orientation, True),
    ("H4", "Full Proposed Heuristic", lambda b: h4_full_proposed, True),
    ("H5", "True-Distance Heuristic (SoCS 2009)", lambda b: TrueDistanceHeuristic(b), True),
]

SEEDED_STAGES = [
    "stage_04", "stage_12", "stage_14", "stage_15", "stage_18",
    "stage_29", "stage_32", "stage_36", "stage_70", "stage_82",
]


def run_ablation_study() -> List[Dict[str, Any]]:
    levels_dir = REPO_ROOT / "bloxorz" / "levels"
    results: List[Dict[str, Any]] = []

    print("=" * 85)
    print("RUNNING EXTENDED ABLATION STUDY (H0 -> H5)")
    print(f"Stages ({len(SEEDED_STAGES)}): {', '.join(SEEDED_STAGES)}")
    print(f"Variants ({len(HEURISTIC_FACTORIES)}): {', '.join(v[0] for v in HEURISTIC_FACTORIES)}")
    print("=" * 85)

    optimal_moves: Dict[str, int] = {}

    for stage_name in SEEDED_STAGES:
        stage_file = levels_dir / f"{stage_name}.json"
        if not stage_file.exists():
            print(f"Warning: {stage_file} not found, skipping.")
            continue

        board = LevelLoader.load_json_level(stage_file)

        # Baseline optimal length
        solver_opt = AstarSolver(heuristic_fn=h4_full_proposed)
        res_opt = solver_opt.solve(board.clone())
        optimal_moves[stage_name] = res_opt.solution_length

        for var_id, var_name, factory, is_admissible in HEURISTIC_FACTORIES:
            heuristic_fn = factory(board)
            solver = AstarSolver(heuristic_fn=heuristic_fn)

            start_time = time.perf_counter()
            res = solver.solve(board.clone())
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0

            peak_mem_kib = round(float(res.peak_memory_kb), 2)
            execution_ms = res.execution_time_ms if res.execution_time_ms > 0 else elapsed_ms
            opt_len = optimal_moves[stage_name]
            moves = res.solution_length
            optimality_gap = moves - opt_len

            record = {
                "stage": stage_name,
                "variant_id": var_id,
                "variant_name": var_name,
                "is_admissible": is_admissible,
                "execution_time_ms": round(execution_ms, 2),
                "peak_memory_kib": round(peak_mem_kib, 2),
                "expanded_nodes": res.expanded_nodes,
                "solution_length": moves,
                "optimal_length": opt_len,
                "optimality_gap": optimality_gap,
                "is_optimal": optimality_gap == 0,
            }
            results.append(record)
            print(
                f"[{stage_name}] {var_id:2s} ({var_name:35s}) -> "
                f"Nodes: {res.expanded_nodes:5d} | "
                f"Time: {execution_ms:7.2f}ms | "
                f"Mem: {peak_mem_kib:7.1f}KiB | "
                f"Moves: {moves:3d} (Gap: {optimality_gap:2d})"
            )

    return results


def save_results(results: List[Dict[str, Any]]) -> None:
    data_dir = REPO_ROOT / "data"
    data_dir.mkdir(exist_ok=True)

    json_path = data_dir / "ablation_results.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved JSON results to {json_path}")

    csv_path = data_dir / "ablation_results.csv"
    if results:
        fieldnames = list(results[0].keys())
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)
    print(f"Saved CSV results to {csv_path}")


if __name__ == "__main__":
    study_results = run_ablation_study()
    save_results(study_results)
