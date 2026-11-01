#!/usr/bin/env python3
"""Generate advanced comparative charts for Bloxorz solver evaluation and ablation study.

Produces publication-grade figures:
  1. ablation_overview.png: 2-panel summary of nodes, runtime, and memory across H0-H5.
  2. ablation_stage_breakdown.png: Per-stage expanded nodes comparison (log scale).
  3. pareto_optimality_tradeoff.png: Search time vs solution optimality ratio (Pareto frontier).
  4. mechanics_pruning_bars.png: Heuristic pruning rate grouped by game mechanics.
"""

import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
ABLATION_CSV = REPO_ROOT / "data" / "ablation_results.csv"
BENCHMARK_JSON = REPO_ROOT / "data" / "benchmark_results.json"
CHART_DIR = REPO_ROOT / "docs" / "report" / "images" / "charts"
CHART_DIR.mkdir(parents=True, exist_ok=True)

# Publication styling
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["DejaVu Sans", "Arial", "Helvetica"],
    "font.size": 10,
    "axes.titlesize": 11,
    "axes.labelsize": 10,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "legend.fontsize": 9,
    "figure.titlesize": 12,
    "axes.edgecolor": "#CBD5E1",
    "axes.linewidth": 1.0,
    "grid.color": "#E2E8F0",
    "grid.linestyle": "--",
    "grid.alpha": 0.7,
})

def plot_ablation_overview(df_ab: pd.DataFrame):
    """Plot average expanded nodes, runtime, and peak memory for H0-H5."""
    summary = df_ab.groupby(["variant_id", "variant_name", "is_admissible"]).agg(
        avg_nodes=("expanded_nodes", "mean"),
        avg_time=("execution_time_ms", "mean"),
        avg_mem=("peak_memory_kib", "mean")
    ).reset_index()

    # Sort in order H0 -> H5
    variant_order = ["H0", "H1", "H2", "H3", "H4", "H5"]
    summary["order"] = summary["variant_id"].apply(lambda x: variant_order.index(x))
    summary = summary.sort_values("order").reset_index(drop=True)

    h0_nodes = summary.loc[summary["variant_id"] == "H0", "avg_nodes"].values[0]
    h0_time = summary.loc[summary["variant_id"] == "H0", "avg_time"].values[0]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.5), constrained_layout=True)

    # Panel 1: Expanded Nodes
    colors = ["#64748B", "#EF4444", "#3B82F6", "#0284C7", "#059669", "#7C3AED"]
    bars1 = ax1.bar(summary["variant_id"], summary["avg_nodes"], color=colors, width=0.6, edgecolor="#334155", linewidth=0.8)
    # Hatch H1 as it is non-admissible
    bars1[1].set_hatch("//")

    ax1.set_ylabel("Số nút mở rộng trung bình (Nodes)", fontweight="bold")
    ax1.set_title("(a) Số lượng nút mở rộng trung bình", fontweight="bold", pad=10)
    ax1.grid(axis="y", linestyle="--", alpha=0.7)
    ax1.set_ylim(0, 2200)

    for bar, (_, row) in zip(bars1, summary.iterrows()):
        val = row["avg_nodes"]
        pct = (val - h0_nodes) / h0_nodes * 100.0
        label_pct = f"{pct:+.1f}%" if row["variant_id"] != "H0" else "Baseline"
        ax1.annotate(
            f"{val:.1f}\n({label_pct})",
            xy=(bar.get_x() + bar.get_width() / 2, val),
            xytext=(0, 4),
            textcoords="offset points",
            ha="center", va="bottom",
            fontsize=8, fontweight="bold",
            color="#0F172A"
        )

    # Custom legend for panel 1
    labels = [
        r"$H_0$: UCS Baseline ($h=0$)",
        r"$H_1$: Unrelaxed Manhattan (Non-admissible)",
        r"$H_2$: Relaxed Manhattan",
        r"$H_3$: Relaxed + Orient Penalty",
        r"$H_4$: Full Proposed (+ Merge)",
        r"$H_5$: True-Distance (SoCS 2009)"
    ]
    ax1.set_xticks(range(6))
    ax1.set_xticklabels([r"$H_0$", r"$H_1^\dagger$", r"$H_2$", r"$H_3$", r"$H_4$", r"$H_5$"], fontweight="bold")

    # Panel 2: Execution Time and Memory
    x = np.arange(len(summary))
    w = 0.35
    ax2_twin = ax2.twinx()

    b_time = ax2.bar(x - w/2, summary["avg_time"], width=w, color="#0284C7", label="Thời gian chạy (ms)", edgecolor="#0369A1")
    b_mem = ax2_twin.bar(x + w/2, summary["avg_mem"], width=w, color="#F59E0B", label="Bộ nhớ đỉnh (KiB)", edgecolor="#D97706")

    ax2.set_ylabel("Thời gian thực thi trung bình (ms)", color="#0284C7", fontweight="bold")
    ax2_twin.set_ylabel("Bộ nhớ đỉnh trung bình (KiB)", color="#D97706", fontweight="bold")
    ax2.set_title("(b) Thời gian thực thi và Mức tiêu thụ bộ nhớ đỉnh", fontweight="bold", pad=10)
    ax2.set_xticks(x)
    ax2.set_xticklabels([r"$H_0$", r"$H_1^\dagger$", r"$H_2$", r"$H_3$", r"$H_4$", r"$H_5$"], fontweight="bold")
    ax2.grid(axis="y", linestyle="--", alpha=0.7)
    ax2_twin.grid(False)

    for bar, val in zip(b_time, summary["avg_time"]):
        ax2.annotate(f"{val:.0f}ms", xy=(bar.get_x() + bar.get_width()/2, val), xytext=(0, 3),
                     textcoords="offset points", ha="center", va="bottom", fontsize=7.5, color="#0284C7")

    # Combine legends
    lines, l_labels = ax2.get_legend_handles_labels()
    lines2, l_labels2 = ax2_twin.get_legend_handles_labels()
    ax2.legend(lines + lines2, l_labels + l_labels2, loc="upper right")

    out_file = CHART_DIR / "ablation_overview.png"
    fig.savefig(out_file, dpi=300)
    plt.close(fig)
    print(f"[OK] Saved {out_file}")


def plot_ablation_stage_breakdown(df_ab: pd.DataFrame):
    """Plot expanded nodes across all 10 stages for H0, H2, H4, H5."""
    stages = ["stage_04", "stage_12", "stage_14", "stage_15", "stage_18",
              "stage_29", "stage_32", "stage_36", "stage_70", "stage_82"]
    stage_labels = [s.replace("stage_", "Stg ") for s in stages]

    piv = df_ab.pivot(index="stage", columns="variant_id", values="expanded_nodes").reindex(stages)

    fig, ax = plt.subplots(figsize=(12, 5), constrained_layout=True)

    x = np.arange(len(stages))
    width = 0.2

    c_h0 = "#64748B"  # Gray
    c_h2 = "#3B82F6"  # Blue
    c_h4 = "#059669"  # Green
    c_h5 = "#7C3AED"  # Purple

    ax.bar(x - 1.5*width, piv["H0"], width, label=r"$H_0$: UCS ($h=0$)", color=c_h0, edgecolor="#334155")
    ax.bar(x - 0.5*width, piv["H2"], width, label=r"$H_2$: Relaxed Manhattan", color=c_h2, edgecolor="#1D4ED8")
    ax.bar(x + 0.5*width, piv["H4"], width, label=r"$H_4$: Full Proposed (+ Merge)", color=c_h4, edgecolor="#047857")
    ax.bar(x + 1.5*width, piv["H5"], width, label=r"$H_5$: True-Distance (SoCS 2009)", color=c_h5, edgecolor="#5B21B6")

    ax.set_yscale("log")
    ax.set_ylabel("Số lượng nút mở rộng (Thang Logarit)", fontweight="bold")
    ax.set_title("So sánh số lượng nút mở rộng theo từng màn chơi giữa các biến thể Heuristic", fontweight="bold", pad=10)
    ax.set_xticks(x)
    ax.set_xticklabels(stage_labels, fontweight="bold")
    ax.grid(axis="y", which="both", linestyle="--", alpha=0.6)
    ax.legend(loc="upper left", framealpha=0.95)

    # Highlight stage 82 and stage 36
    ax.annotate(r"$\mathbf{-89.5\%}$", xy=(9 + 1.5*width, piv.loc["stage_82", "H5"]),
                xytext=(0, 8), textcoords="offset points", ha="center", fontsize=8, fontweight="bold", color="#7C3AED")
    ax.annotate(r"$\mathbf{-85.5\%}$", xy=(7 + 1.5*width, piv.loc["stage_36", "H5"]),
                xytext=(0, 8), textcoords="offset points", ha="center", fontsize=8, fontweight="bold", color="#7C3AED")

    out_file = CHART_DIR / "ablation_stage_breakdown.png"
    fig.savefig(out_file, dpi=300)
    plt.close(fig)
    print(f"[OK] Saved {out_file}")


def plot_pareto_optimality(df_bench: pd.DataFrame, df_ab: pd.DataFrame):
    """Plot search execution time vs solution optimality ratio (Pareto frontier)."""
    fig, ax = plt.subplots(figsize=(9, 5.2), constrained_layout=True)

    # Get optimal lengths from ablation dataframe
    opt_lens = df_ab.groupby("stage")["optimal_length"].first().to_dict()

    algo_styles = {
        "BFS": {"color": "#0284C7", "marker": "o", "label": "BFS (Duyệt theo chiều rộng)"},
        "DFS": {"color": "#E11D48", "marker": "s", "label": "DFS (Duyệt theo chiều sâu)"},
        "UCS": {"color": "#D97706", "marker": "^", "label": "UCS (Chi phí đồng nhất)"},
        "A*":  {"color": "#059669", "marker": "D", "label": r"A* với $H_4$ đề xuất"},
    }

    for algo, style in algo_styles.items():
        sub = df_bench[df_bench["algorithm"] == algo]
        times = sub["search_time_ms"].values
        sub_lens = sub["solution_length"].values
        stages = sub["stage"].values
        ratios = [l / opt_lens[st] for l, st in zip(sub_lens, stages)]

        ax.scatter(times, ratios, color=style["color"], marker=style["marker"],
                   s=65, alpha=0.85, edgecolors="#0F172A", linewidth=0.7, label=style["label"])

    # Add H5 data points
    sub_h5 = df_ab[df_ab["variant_id"] == "H5"]
    times_h5 = sub_h5["execution_time_ms"].values
    ratios_h5 = [1.0] * len(times_h5)
    ax.scatter(times_h5, ratios_h5, color="#7C3AED", marker="P", s=75, alpha=0.9,
               edgecolors="#0F172A", linewidth=0.8, label=r"A* với $H_5$ True-Distance (SoCS)")

    # Optimal line
    ax.axhline(1.0, color="#10B981", linestyle="--", linewidth=1.4, alpha=0.8, label="Đường chuẩn tối ưu tuyệt đối (Ratio = 1.0)")

    ax.set_xscale("log")
    ax.set_xlabel("Thời gian tìm kiếm (ms, Thang Logarit)", fontweight="bold")
    ax.set_ylabel(r"Tỷ số dưới tối ưu độ dài lộ trình ($L_{\text{found}} / L^*$)", fontweight="bold")
    ax.set_title("Biểu đồ đánh đổi Pareto: Thời gian tìm kiếm và Tính tối ưu của lời giải", fontweight="bold", pad=10)
    ax.grid(True, which="both", linestyle="--", alpha=0.6)
    ax.set_ylim(0.7, 11.5)

    # Annotate DFS extreme suboptimality at stage 82
    ax.annotate("DFS tại Stage 82:\n273 bước vs 26 bước tối ưu (10.5x)",
                xy=(276.0, 10.5), xytext=(350, 9.2),
                arrowprops=dict(arrowstyle="->", color="#E11D48", lw=1.2),
                fontsize=8.5, fontweight="bold", color="#E11D48")

    # Annotate Pareto Frontier area
    ax.annotate("Vùng Pareto tối ưu\n(Nhanh nhất & Tối ưu 100%)",
                xy=(9.0, 1.0), xytext=(5.0, 2.3),
                arrowprops=dict(arrowstyle="->", color="#059669", lw=1.2),
                fontsize=8.5, fontweight="bold", color="#059669")

    ax.legend(loc="upper right", framealpha=0.95, facecolor="white")

    out_file = CHART_DIR / "pareto_optimality_tradeoff.png"
    fig.savefig(out_file, dpi=300)
    plt.close(fig)
    print(f"[OK] Saved {out_file}")


def plot_mechanics_pruning(df_ab: pd.DataFrame, df_bench: pd.DataFrame):
    """Plot pruning rate grouped by mechanics: Standard, Fragile, Switches/Bridges, Split/Teleport."""
    stage_mechanics = {
        "stage_04": "Gạch mong manh (Fragile)",
        "stage_12": "Cầu & Công tắc",
        "stage_14": "Cầu & Công tắc",
        "stage_15": "Phân thân (Split/Teleport)",
        "stage_18": "Cầu & Công tắc",
        "stage_29": "Cầu & Công tắc",
        "stage_32": "Cầu & Công tắc",
        "stage_36": "Sàn cơ bản (Standard)",
        "stage_70": "Cầu & Công tắc",
        "stage_82": "Phân thân (Split/Teleport)",
    }

    df_copy = df_ab.copy()
    df_copy["mechanic"] = df_copy["stage"].map(stage_mechanics)

    # Compute baseline H0 nodes per stage
    h0_nodes = df_copy[df_copy["variant_id"] == "H0"].set_index("stage")["expanded_nodes"].to_dict()
    df_copy["h0_nodes"] = df_copy["stage"].map(h0_nodes)
    df_copy["pruning_rate"] = (1.0 - df_copy["expanded_nodes"] / df_copy["h0_nodes"]) * 100.0

    mech_order = [
        "Sàn cơ bản (Standard)",
        "Gạch mong manh (Fragile)",
        "Cầu & Công tắc",
        "Phân thân (Split/Teleport)"
    ]

    grouped = df_copy.groupby(["mechanic", "variant_id"])["pruning_rate"].mean().unstack()
    grouped = grouped.reindex(mech_order)

    fig, ax = plt.subplots(figsize=(10, 4.8), constrained_layout=True)

    x = np.arange(len(mech_order))
    width = 0.22

    ax.bar(x - width, grouped["H2"], width, label=r"$H_2$: Relaxed Manhattan", color="#3B82F6", edgecolor="#1E40AF")
    ax.bar(x, grouped["H4"], width, label=r"$H_4$: Full Proposed (+ Merge)", color="#059669", edgecolor="#065F46")
    ax.bar(x + width, grouped["H5"], width, label=r"$H_5$: True-Distance (SoCS)", color="#7C3AED", edgecolor="#5B21B6")

    ax.set_ylabel("Tỷ lệ cắt tỉa trung bình (%) so với Baseline UCS", fontweight="bold")
    ax.set_title("Năng lực cắt tỉa không gian tìm kiếm phân nhóm theo đặc trưng cơ học bản đồ", fontweight="bold", pad=10)
    ax.set_xticks(x)
    ax.set_xticklabels(mech_order, fontweight="bold")
    ax.set_ylim(-5, 95)
    ax.grid(axis="y", linestyle="--", alpha=0.7)
    ax.legend(loc="upper left")

    # Add percentage labels
    for i in range(len(mech_order)):
        for j, var in enumerate(["H2", "H4", "H5"]):
            val = grouped.loc[mech_order[i], var]
            pos_x = x[i] + (j - 1) * width
            ax.annotate(f"{val:.1f}%", xy=(pos_x, val), xytext=(0, 3),
                        textcoords="offset points", ha="center", va="bottom",
                        fontsize=8, fontweight="bold", color="#1E293B")

    out_file = CHART_DIR / "mechanics_pruning_bars.png"
    fig.savefig(out_file, dpi=300)
    plt.close(fig)
    print(f"[OK] Saved {out_file}")


def main():
    print("Loading benchmark and ablation datasets...")
    df_ab = pd.read_csv(ABLATION_CSV)
    with open(BENCHMARK_JSON, "r", encoding="utf-8") as f:
        bench_data = json.load(f)
    df_bench = pd.DataFrame(bench_data)

    plot_ablation_overview(df_ab)
    plot_ablation_stage_breakdown(df_ab)
    plot_pareto_optimality(df_bench, df_ab)
    plot_mechanics_pruning(df_ab, df_bench)
    print("All extended figures generated successfully!")


if __name__ == "__main__":
    main()
