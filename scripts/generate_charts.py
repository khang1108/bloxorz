#!/usr/bin/env python3
"""Generate comparative charts and plots from benchmark results.

Produces high-resolution figures comparing BFS, DFS, UCS, and A* across:
  1. Search Execution Time / Latency (ms) [Log scale]
  2. Peak Memory Consumption (KiB) [Log scale]
  3. Number of Expanded Nodes [Log scale]
  4. Solution Length (Number of Moves) [Optimality comparison]
  5. Comprehensive 4-Panel Benchmark Dashboard
"""

import json
from pathlib import Path
from typing import Dict, List
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = REPO_ROOT / "data" / "benchmark_results.json"
OUTPUT_DIRS = [
    REPO_ROOT / "docs" / "report" / "images" / "charts",
    REPO_ROOT / "data" / "charts",
]

# Ensure output directories exist
for out_dir in OUTPUT_DIRS:
    out_dir.mkdir(parents=True, exist_ok=True)

# Color tokens for the 4 algorithms
COLORS = {
    "BFS": "#0284C7",  # Vivid Cyan / Blue
    "DFS": "#E11D48",  # Crimson / Red
    "UCS": "#D97706",  # Amber / Gold
    "A*":  "#059669",  # Emerald / Green
}

# Typography and plot style
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["DejaVu Sans", "Arial", "Helvetica"],
    "axes.edgecolor": "#CBD5E1",
    "axes.linewidth": 1.0,
    "grid.color": "#E2E8F0",
    "grid.linestyle": "--",
    "grid.alpha": 0.7,
})


def load_data():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def prepare_matrix(data: List[Dict]):
    stages = []
    seen = set()
    for row in data:
        st = row["stage"]
        if st not in seen:
            seen.add(st)
            stages.append(st)

    # Sort stages numerically
    stages.sort(key=lambda s: int(s.split("_")[1]) if "_" in s else 0)
    algorithms = ["BFS", "DFS", "UCS", "A*"]

    # Matrices: [algo][stage_idx]
    metrics = {
        "time": {a: [] for a in algorithms},
        "memory": {a: [] for a in algorithms},
        "expanded": {a: [] for a in algorithms},
        "moves": {a: [] for a in algorithms},
        "cost": {a: [] for a in algorithms},
    }

    by_stage_algo = {(r["stage"], r["algorithm"]): r for r in data}

    for st in stages:
        for a in algorithms:
            r = by_stage_algo.get((st, a), {})
            metrics["time"][a].append(r.get("search_time_ms", 0.0))
            metrics["memory"][a].append(r.get("peak_memory_kib", 0.0))
            metrics["expanded"][a].append(r.get("expanded_nodes", 0))
            metrics["moves"][a].append(r.get("solution_length", 0))
            metrics["cost"][a].append(r.get("solution_cost", 0.0) or 0.0)

    # Clean display labels for stages
    stage_labels = [s.replace("stage_", "Stg ") for s in stages]
    return stages, stage_labels, algorithms, metrics


def save_fig(fig, filename: str):
    for out_dir in OUTPUT_DIRS:
        dest = out_dir / filename
        fig.savefig(dest, dpi=300, bbox_inches="tight")
    print(f"[OK] Saved chart: {filename}")


def plot_metric_bar(stages, stage_labels, algorithms, metrics, metric_key, title, ylabel, filename, log_scale=False):
    x = np.arange(len(stages))
    width = 0.20
    fig, ax = plt.subplots(figsize=(12, 6))

    for idx, algo in enumerate(algorithms):
        offset = (idx - 1.5) * width
        values = metrics[metric_key][algo]
        bars = ax.bar(x + offset, values, width, label=algo, color=COLORS[algo], alpha=0.92)

    ax.set_title(title, fontsize=14, fontweight="bold", pad=14, color="#0F172A")
    ax.set_ylabel(ylabel, fontsize=11, fontweight="bold", color="#334155")
    ax.set_xlabel("Sampled Test Stages (Random Seed = 42)", fontsize=11, fontweight="bold", labelpad=10, color="#334155")
    ax.set_xticks(x)
    ax.set_xticklabels(stage_labels, fontsize=10, fontweight="bold")
    ax.legend(frameon=True, facecolor="white", edgecolor="#CBD5E1", fontsize=10)
    ax.grid(axis="y", linestyle="--", alpha=0.7)

    if log_scale:
        ax.set_yscale("log")
        ax.set_ylabel(f"{ylabel} (Logarithmic Scale)", fontsize=11, fontweight="bold", color="#334155")

    fig.tight_layout()
    save_fig(fig, filename)
    plt.close(fig)


def plot_solution_optimality(stages, stage_labels, algorithms, metrics):
    x = np.arange(len(stages))
    width = 0.20
    fig, ax = plt.subplots(figsize=(12, 6))

    for idx, algo in enumerate(algorithms):
        offset = (idx - 1.5) * width
        values = metrics["moves"][algo]
        ax.bar(x + offset, values, width, label=algo, color=COLORS[algo], alpha=0.90)

    ax.set_title("Solution Length (Number of Moves) Comparison: Optimality vs Heuristics",
                 fontsize=14, fontweight="bold", pad=14, color="#0F172A")
    ax.set_ylabel("Solution Length (Physical Moves)", fontsize=11, fontweight="bold", color="#334155")
    ax.set_xlabel("Sampled Test Stages", fontsize=11, fontweight="bold", labelpad=10, color="#334155")
    ax.set_xticks(x)
    ax.set_xticklabels(stage_labels, fontsize=10, fontweight="bold")
    ax.legend(frameon=True, facecolor="white", edgecolor="#CBD5E1", fontsize=10)
    ax.grid(axis="y", linestyle="--", alpha=0.7)

    fig.tight_layout()
    save_fig(fig, "comparison_solution_length.png")
    plt.close(fig)


def plot_summary_dashboard(stages, stage_labels, algorithms, metrics):
    fig, axes = plt.subplots(2, 2, figsize=(16, 11))
    x = np.arange(len(stages))
    width = 0.20

    panels = [
        (axes[0, 0], "time", "Search Execution Time (ms) [Log Scale]", "Search Time (ms)", True),
        (axes[0, 1], "memory", "Peak Memory Consumption (KiB) [Log Scale]", "Peak Memory (KiB)", True),
        (axes[1, 0], "expanded", "Number of Expanded Nodes [Log Scale]", "Expanded Nodes", True),
        (axes[1, 1], "moves", "Solution Length (Number of Moves)", "Moves Count", False),
    ]

    for ax, metric_key, title, ylabel, is_log in panels:
        for idx, algo in enumerate(algorithms):
            offset = (idx - 1.5) * width
            values = metrics[metric_key][algo]
            ax.bar(x + offset, values, width, label=algo, color=COLORS[algo], alpha=0.90)

        ax.set_title(title, fontsize=12, fontweight="bold", pad=10, color="#0F172A")
        ax.set_ylabel(ylabel, fontsize=10, fontweight="bold", color="#334155")
        ax.set_xticks(x)
        ax.set_xticklabels(stage_labels, fontsize=9)
        ax.grid(axis="y", linestyle="--", alpha=0.6)
        if is_log:
            ax.set_yscale("log")
        ax.legend(frameon=True, facecolor="white", edgecolor="#CBD5E1", fontsize=9, loc="upper left")

    fig.suptitle("Bloxorz Search Algorithms Performance Benchmark (Seed 42)",
                 fontsize=16, fontweight="bold", y=0.99, color="#0F172A")
    fig.tight_layout()
    save_fig(fig, "benchmark_dashboard_2x2.png")
    plt.close(fig)


def plot_time_vs_expanded_scatter(data: List[Dict]):
    fig, ax = plt.subplots(figsize=(10, 6))

    for algo, c in COLORS.items():
        algo_data = [r for r in data if r["algorithm"] == algo]
        nodes = [r["expanded_nodes"] for r in algo_data]
        times = [r["search_time_ms"] for r in algo_data]
        ax.scatter(nodes, times, label=algo, color=c, alpha=0.85, s=80, edgecolors="white", linewidth=1.2)

    ax.set_title("Search Time vs Expanded Nodes (Efficiency Correlation)",
                 fontsize=14, fontweight="bold", pad=14, color="#0F172A")
    ax.set_xlabel("Number of Expanded Nodes (Log Scale)", fontsize=11, fontweight="bold", color="#334155")
    ax.set_ylabel("Search Time in ms (Log Scale)", fontsize=11, fontweight="bold", color="#334155")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.grid(True, linestyle="--", alpha=0.7)
    ax.legend(frameon=True, facecolor="white", edgecolor="#CBD5E1", fontsize=10)

    fig.tight_layout()
    save_fig(fig, "scatter_time_vs_expanded.png")
    plt.close(fig)


def main():
    data = load_data()
    stages, stage_labels, algorithms, metrics = prepare_matrix(data)

    print("Generating comprehensive benchmark charts...")
    # 1. Search Time
    plot_metric_bar(stages, stage_labels, algorithms, metrics, "time",
                    "Search Execution Time Comparison across Stages",
                    "Time (ms)", "comparison_search_time.png", log_scale=True)

    # 2. Peak Memory
    plot_metric_bar(stages, stage_labels, algorithms, metrics, "memory",
                    "Peak Memory Usage Comparison across Stages",
                    "Peak Memory (KiB)", "comparison_peak_memory.png", log_scale=True)

    # 3. Expanded Nodes
    plot_metric_bar(stages, stage_labels, algorithms, metrics, "expanded",
                    "State-Space Exploration (Expanded Nodes) Comparison",
                    "Expanded Nodes", "comparison_expanded_nodes.png", log_scale=True)

    # 4. Solution Length (Moves)
    plot_solution_optimality(stages, stage_labels, algorithms, metrics)

    # 5. Dashboard 2x2
    plot_summary_dashboard(stages, stage_labels, algorithms, metrics)

    # 6. Scatter Correlation
    plot_time_vs_expanded_scatter(data)

    print("\n[DONE] All charts generated successfully!")


if __name__ == "__main__":
    main()

