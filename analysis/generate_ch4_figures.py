from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Reuse existing project analysis helpers (repo-local, no absolute paths)
from analyze_results import (
    ensure_dirs,
    load_counts,
    load_eval_summary,
    load_pruned_rows,
    load_transform_summary,
    load_score_summary,
    TABLE_DIR,
    FIG_DIR,
)


CATEGORY_ORDER = [
    "random",
    "polynomial",
    "prime",
    "combinatorics",
    "graph_lattice_path",
    "all_500",
]

CATEGORY_LABEL = {
    "random": "Random",
    "polynomial": "Polynomial",
    "prime": "Prime",
    "combinatorics": "Combinatorics",
    "graph_lattice_path": "Graph/Lattice/Path",
    "all_500": "All 500",
}


def set_plot_style() -> None:
    plt.rcParams.update(
        {
            "figure.dpi": 170,
            "savefig.dpi": 330,
            "font.size": 11,
            "axes.titlesize": 13,
            "axes.labelsize": 11,
            "legend.fontsize": 10,
            "xtick.labelsize": 10,
            "ytick.labelsize": 10,
            "axes.grid": True,
            "grid.alpha": 0.22,
            "grid.linestyle": "--",
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )


def save_tables() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Build the same summary tables used in chapter analysis and persist them.
    This keeps figure generation reproducible from repository data.
    """
    counts_df = load_counts()
    eval_df = load_eval_summary()
    pruned_df = load_pruned_rows()
    transform_df = load_transform_summary(pruned_df)
    score_df = load_score_summary(pruned_df)

    counts_df.to_csv(TABLE_DIR / "counts_summary.csv", index=False)
    eval_df.to_csv(TABLE_DIR / "evaluation_summary.csv", index=False)
    transform_df.to_csv(TABLE_DIR / "transform_summary_pruned.csv", index=False)
    score_df.to_csv(TABLE_DIR / "score_summary_pruned.csv", index=False)

    return counts_df, eval_df, transform_df, score_df


def plot_accuracy_grouped(eval_df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(12.4, 6.3))
    x = np.arange(len(CATEGORY_ORDER))
    width = 0.23

    for i, k in enumerate([1, 5, 10]):
        vals = [
            float(eval_df[(eval_df["category"] == c) & (eval_df["k"] == k)]["accuracy"].iloc[0])
            for c in CATEGORY_ORDER
        ]
        bars = ax.bar(x + (i - 1) * width, vals, width=width, label=f"Accuracy@{k}")
        for b, v in zip(bars, vals):
            ax.text(
                b.get_x() + b.get_width() / 2,
                b.get_height() + 0.007,
                f"{v * 100:.1f}%",
                ha="center",
                va="bottom",
                fontsize=9,
            )

    ax.set_xticks(x)
    ax.set_xticklabels([CATEGORY_LABEL[c] for c in CATEGORY_ORDER], rotation=16, ha="right")
    ax.set_ylim(0.82, 1.0)
    ax.set_ylabel("Accuracy")
    ax.set_title("Rediscovery Accuracy by Query Set")
    ax.legend(frameon=False, ncols=3, loc="upper center", bbox_to_anchor=(0.5, 1.12))

    fig.tight_layout()
    fig.savefig(FIG_DIR / "ch4_accuracy_by_category_k_v2.png", bbox_inches="tight")
    plt.close(fig)


def plot_pruning_retention(counts_df: pd.DataFrame) -> None:
    df = counts_df.set_index("category").loc[CATEGORY_ORDER].reset_index()
    raw = df["raw_rows"].to_numpy()
    pruned = df["pruned_rows"].to_numpy()
    retained = (pruned / raw) * 100.0

    fig, ax = plt.subplots(figsize=(12.4, 6.2))
    bars = ax.bar(
        np.arange(len(CATEGORY_ORDER)),
        retained,
        color=["#3b82f6", "#06b6d4", "#22c55e", "#f59e0b", "#ef4444", "#8b5cf6"],
    )

    for b, r, p in zip(bars, raw, pruned):
        ax.text(
            b.get_x() + b.get_width() / 2,
            b.get_height() + 0.55,
            f"{int(p)}/{int(r)}",
            ha="center",
            va="bottom",
            fontsize=9,
        )

    ax.set_xticks(np.arange(len(CATEGORY_ORDER)))
    ax.set_xticklabels([CATEGORY_LABEL[c] for c in CATEGORY_ORDER], rotation=16, ha="right")
    ax.set_ylim(45, 65)
    ax.set_ylabel("Pruned rows retained from raw (%)")
    ax.set_title("Pruning Retention by Query Set")

    fig.tight_layout()
    fig.savefig(FIG_DIR / "ch4_pruning_retention_v2.png", bbox_inches="tight")
    plt.close(fig)


def plot_transform_profile_500(transform_df: pd.DataFrame) -> None:
    t500 = (
        transform_df[transform_df["category"] == "all_500"]
        .sort_values("rows", ascending=False)
        .head(11)
        .reset_index(drop=True)
    )

    fig, ax = plt.subplots(figsize=(10.8, 6.3))
    y = np.arange(len(t500))
    ax.barh(y, t500["share_pct"], color="#2563eb")
    ax.set_yticks(y)
    ax.set_yticklabels(t500["transform"])
    ax.invert_yaxis()

    for yi, sp, rw in zip(y, t500["share_pct"], t500["rows"]):
        ax.text(float(sp) + 0.35, yi, f"{float(sp):.2f}% ({int(rw)})", va="center", fontsize=9)

    ax.set_xlabel("Share of pruned rows (%)")
    ax.set_title("Transform Contribution in the 500-Query Experiment")
    ax.set_xlim(0, float(t500["share_pct"].max()) + 9)

    fig.tight_layout()
    fig.savefig(FIG_DIR / "ch4_transform_profile_500_v2.png", bbox_inches="tight")
    plt.close(fig)


def plot_accuracy_runtime_tradeoff(eval_df: pd.DataFrame) -> None:
    r10 = eval_df[eval_df["k"] == 10].set_index("category").loc[CATEGORY_ORDER].reset_index()
    xs = r10["avg_seconds"].to_numpy()
    ys = (r10["accuracy"] * 100.0).to_numpy()

    fig, ax = plt.subplots(figsize=(10.8, 6.1))
    ax.scatter(
        xs,
        ys,
        s=95,
        c=["#3b82f6", "#06b6d4", "#22c55e", "#f59e0b", "#ef4444", "#8b5cf6"],
    )

    for x0, y0, cat in zip(xs, ys, r10["category"]):
        ax.annotate(CATEGORY_LABEL[str(cat)], (x0, y0), textcoords="offset points", xytext=(7, 5), fontsize=9)

    ax.set_xlabel("Average runtime per query (seconds)")
    ax.set_ylabel("Accuracy@10 (%)")
    ax.set_title("Accuracy-Runtime Profile by Query Set")
    ax.set_xlim(float(xs.min()) - 0.004, float(xs.max()) + 0.004)
    ax.set_ylim(88, 98)

    fig.tight_layout()
    fig.savefig(FIG_DIR / "ch4_accuracy_runtime_tradeoff_v2.png", bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    ensure_dirs()
    set_plot_style()

    counts_df, eval_df, transform_df, _score_df = save_tables()

    plot_accuracy_grouped(eval_df)
    plot_pruning_retention(counts_df)
    plot_transform_profile_500(transform_df)
    plot_accuracy_runtime_tradeoff(eval_df)

    generated = sorted(p.name for p in FIG_DIR.glob("ch4_*_v2.png"))
    print("Generated Chapter 4 figures:")
    for name in generated:
        print(f" - {name}")
    print(f"\nFigures directory: {FIG_DIR}")
    print(f"Tables directory:  {TABLE_DIR}")


if __name__ == "__main__":
    main()
