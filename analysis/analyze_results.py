from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
TESTS_DIR = ROOT / "tests"
OUT_DIR = ROOT / "analysis" / "output"
FIG_DIR = OUT_DIR / "figures"
TABLE_DIR = OUT_DIR / "tables"


CATEGORIES: List[Dict[str, str]] = [
    {"label": "random", "folder": "random", "prefix": "random", "eval": "eval_random.csv"},
    {"label": "polynomial", "folder": "polynomial", "prefix": "poly", "eval": "eval_poly.csv"},
    {"label": "prime", "folder": "prime", "prefix": "prime", "eval": "eval_prime.csv"},
    {"label": "combinatorics", "folder": "combinatronics", "prefix": "combo", "eval": "eval_combo.csv"},
    {"label": "graph_lattice_path", "folder": "graph:lattice:path", "prefix": "graph", "eval": "eval_graph.csv"},
    {"label": "all_500", "folder": "500_queries", "prefix": "500", "eval": "eval_500.csv"},
]


def ensure_dirs() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    TABLE_DIR.mkdir(parents=True, exist_ok=True)


def row_count(path: Path) -> int:
    with path.open("r", encoding="utf-8", newline="") as f:
        return max(sum(1 for _ in f) - 1, 0)


def load_counts() -> pd.DataFrame:
    rows: List[Dict[str, object]] = []
    for cfg in CATEGORIES:
        label = cfg["label"]
        folder = cfg["folder"]
        prefix = cfg["prefix"]
        base = TESTS_DIR / folder
        raw = base / f"report_{prefix}_raw.csv"
        no_self = base / f"report_{prefix}_no_self.csv"
        pruned = base / f"report_{prefix}_pruned.csv"
        rows.append(
            {
                "category": label,
                "raw_rows": row_count(raw),
                "no_self_rows": row_count(no_self),
                "pruned_rows": row_count(pruned),
            }
        )
    df = pd.DataFrame(rows)
    df["self_removed_rows"] = df["raw_rows"] - df["no_self_rows"]
    df["pruned_out_rows"] = df["no_self_rows"] - df["pruned_rows"]
    df["retained_vs_raw_pct"] = (100 * df["pruned_rows"] / df["raw_rows"]).round(2)
    df["retained_vs_no_self_pct"] = (100 * df["pruned_rows"] / df["no_self_rows"]).round(2)
    return df


def load_eval_summary() -> pd.DataFrame:
    rows: List[Dict[str, object]] = []
    for cfg in CATEGORIES:
        label = cfg["label"]
        folder = cfg["folder"]
        eval_path = TESTS_DIR / folder / cfg["eval"]
        df = pd.read_csv(eval_path)
        df["found"] = df["found"].astype(int)
        for k, g in df.groupby("k"):
            rows.append(
                {
                    "category": label,
                    "k": int(k),
                    "queries": int(len(g)),
                    "found": int(g["found"].sum()),
                    "accuracy": float(g["found"].mean()),
                    "avg_seconds": float(g["seconds"].astype(float).mean()),
                    "median_seconds": float(g["seconds"].astype(float).median()),
                }
            )
    out = pd.DataFrame(rows).sort_values(["category", "k"]).reset_index(drop=True)
    out["accuracy_pct"] = (100 * out["accuracy"]).round(2)
    return out


def load_pruned_rows() -> pd.DataFrame:
    dfs: List[pd.DataFrame] = []
    for cfg in CATEGORIES:
        label = cfg["label"]
        folder = cfg["folder"]
        prefix = cfg["prefix"]
        path = TESTS_DIR / folder / f"report_{prefix}_pruned.csv"
        df = pd.read_csv(path)
        df["category"] = label
        df["score"] = pd.to_numeric(df["score"], errors="coerce").fillna(0).astype(int)
        df["normalized_score"] = pd.to_numeric(df["normalized_score"], errors="coerce").fillna(0.0)
        dfs.append(df)
    return pd.concat(dfs, ignore_index=True)


def load_transform_summary(pruned: pd.DataFrame) -> pd.DataFrame:
    g = (
        pruned.groupby(["category", "transform"], as_index=False)
        .size()
        .rename(columns={"size": "rows"})
    )
    totals = g.groupby("category")["rows"].transform("sum")
    g["share_pct"] = (100 * g["rows"] / totals).round(2)
    return g.sort_values(["category", "rows"], ascending=[True, False]).reset_index(drop=True)


def load_score_summary(pruned: pd.DataFrame) -> pd.DataFrame:
    q = (
        pruned.groupby("category")
        .agg(
            rows=("score", "size"),
            mean_score=("score", "mean"),
            median_score=("score", "median"),
            p90_score=("score", lambda s: float(np.quantile(s, 0.90))),
            mean_norm=("normalized_score", "mean"),
            median_norm=("normalized_score", "median"),
            p90_norm=("normalized_score", lambda s: float(np.quantile(s, 0.90))),
        )
        .reset_index()
    )
    for col in ["mean_score", "median_score", "p90_score", "mean_norm", "median_norm", "p90_norm"]:
        q[col] = q[col].round(4)
    return q


def plot_accuracy(eval_df: pd.DataFrame) -> None:
    cats = list(eval_df["category"].drop_duplicates())
    k_values = sorted(eval_df["k"].unique())
    x = np.arange(len(cats))
    width = 0.24

    plt.figure(figsize=(11, 5))
    for i, k in enumerate(k_values):
        vals = []
        for c in cats:
            v = eval_df[(eval_df["category"] == c) & (eval_df["k"] == k)]["accuracy"].iloc[0]
            vals.append(v)
        plt.bar(x + (i - 1) * width, vals, width=width, label=f"accuracy@{k}")

    plt.xticks(x, cats, rotation=20)
    plt.ylim(0.0, 1.0)
    plt.ylabel("Accuracy")
    plt.title("Retrieval Accuracy by Category")
    plt.legend()
    plt.tight_layout()
    plt.savefig(FIG_DIR / "accuracy_by_category_k.png", dpi=200)
    plt.close()


def plot_pruning_funnel(counts_df: pd.DataFrame) -> None:
    cats = counts_df["category"].tolist()
    x = np.arange(len(cats))
    width = 0.25

    plt.figure(figsize=(11, 5))
    plt.bar(x - width, counts_df["raw_rows"], width=width, label="raw")
    plt.bar(x, counts_df["no_self_rows"], width=width, label="no_self")
    plt.bar(x + width, counts_df["pruned_rows"], width=width, label="pruned")
    plt.xticks(x, cats, rotation=20)
    plt.ylabel("Rows")
    plt.title("Rows Before/After Filtering and Pruning")
    plt.legend()
    plt.tight_layout()
    plt.savefig(FIG_DIR / "pruning_funnel.png", dpi=200)
    plt.close()


def plot_transform_heatmap(transform_df: pd.DataFrame) -> None:
    pivot = transform_df.pivot(index="category", columns="transform", values="share_pct").fillna(0.0)
    pivot = pivot.loc[:, sorted(pivot.columns)]

    plt.figure(figsize=(13, 4.8))
    arr = pivot.to_numpy(dtype=float)
    im = plt.imshow(arr, aspect="auto")
    plt.colorbar(im, label="Share %")
    plt.yticks(np.arange(len(pivot.index)), pivot.index)
    plt.xticks(np.arange(len(pivot.columns)), pivot.columns, rotation=50, ha="right")
    plt.title("Transform Distribution (Pruned Reports, %)")
    plt.tight_layout()
    plt.savefig(FIG_DIR / "transform_share_heatmap.png", dpi=200)
    plt.close()


def plot_norm_box(pruned: pd.DataFrame) -> None:
    cats = [c["label"] for c in CATEGORIES]
    data = [pruned.loc[pruned["category"] == c, "normalized_score"].to_numpy() for c in cats]

    plt.figure(figsize=(11, 5))
    plt.boxplot(data, tick_labels=cats, showfliers=False)
    plt.xticks(rotation=20)
    plt.ylabel("normalized_score")
    plt.title("Normalized Score Distribution by Category (Pruned)")
    plt.tight_layout()
    plt.savefig(FIG_DIR / "normalized_score_boxplot.png", dpi=200)
    plt.close()


def write_markdown_summary(counts_df: pd.DataFrame, eval_df: pd.DataFrame, transform_df: pd.DataFrame, score_df: pd.DataFrame) -> None:
    out_md = OUT_DIR / "results_summary.md"

    def best_acc_for_cat(cat: str) -> Tuple[int, float]:
        s = eval_df[eval_df["category"] == cat].sort_values("accuracy", ascending=False).iloc[0]
        return int(s["k"]), float(s["accuracy"])

    lines: List[str] = []
    lines.append("# OEIS Mining Results Summary")
    lines.append("")
    lines.append("## Key points")
    lines.append("")
    mean_acc_at1 = eval_df[eval_df["k"] == 1]["accuracy"].mean()
    mean_acc_at10 = eval_df[eval_df["k"] == 10]["accuracy"].mean()
    lines.append(f"- Mean accuracy@1 across all test sets: **{mean_acc_at1:.3f}**.")
    lines.append(f"- Mean accuracy@10 across all test sets: **{mean_acc_at10:.3f}**.")
    top_t = (
        transform_df.groupby("transform", as_index=False)["rows"].sum().sort_values("rows", ascending=False).iloc[0]
    )
    lines.append(f"- Most frequent transform after pruning: **{top_t['transform']}** ({int(top_t['rows'])} rows total).")
    lines.append("")
    lines.append("## Category observations")
    lines.append("")
    for cat in counts_df["category"]:
        c = counts_df[counts_df["category"] == cat].iloc[0]
        bk, ba = best_acc_for_cat(cat)
        lines.append(
            f"- **{cat}**: raw={int(c['raw_rows'])}, pruned={int(c['pruned_rows'])} "
            f"(retained {c['retained_vs_raw_pct']:.2f}% of raw). Best accuracy at k={bk}: {ba:.3f}."
        )
    lines.append("")
    lines.append("## Generated artifacts")
    lines.append("")
    lines.append("- Tables: `analysis/output/tables/*.csv`")
    lines.append("- Figures: `analysis/output/figures/*.png`")

    out_md.write_text("\n".join(lines), encoding="utf-8")


def write_dissertation_template(counts_df: pd.DataFrame, eval_df: pd.DataFrame, transform_df: pd.DataFrame, score_df: pd.DataFrame) -> None:
    path = OUT_DIR / "dissertation_template.md"
    overall = score_df[score_df["category"] == "all_500"].iloc[0]
    eval500 = eval_df[eval_df["category"] == "all_500"].sort_values("k")
    acc1 = eval500[eval500["k"] == 1]["accuracy"].iloc[0]
    acc5 = eval500[eval500["k"] == 5]["accuracy"].iloc[0]
    acc10 = eval500[eval500["k"] == 10]["accuracy"].iloc[0]

    top_transform = (
        transform_df[transform_df["category"] == "all_500"]
        .sort_values("rows", ascending=False)
        .iloc[0]
    )
    counts500 = counts_df[counts_df["category"] == "all_500"].iloc[0]

    lines: List[str] = []
    lines.append("# Dissertation Results Template")
    lines.append("")
    lines.append("## Suggested Results Narrative")
    lines.append("")
    lines.append(
        "The system was evaluated on six query sets: five thematic sets of 100 OEIS IDs "
        "(random, polynomial, prime, combinatorics, graph/lattice/path) and one combined set of 500 queries."
    )
    lines.append(
        f"For the 500-query benchmark, retrieval accuracy was {acc1:.3f} at k=1, {acc5:.3f} at k=5, and {acc10:.3f} at k=10."
    )
    lines.append(
        f"Filtering and pruning reduced the raw candidate set from {int(counts500['raw_rows'])} to {int(counts500['pruned_rows'])} rows "
        f"({counts500['retained_vs_raw_pct']:.2f}% retained), improving result readability."
    )
    lines.append(
        f"In pruned results, the most frequent transform was {top_transform['transform']} "
        f"({int(top_transform['rows'])} rows, {top_transform['share_pct']:.2f}% of all 500-query pruned rows), "
        "indicating that low-modulus arithmetic equivalence is a dominant source of discovered links."
    )
    lines.append(
        f"The mean pruned match score for the 500-query set was {overall['mean_score']:.4f} "
        f"(median {overall['median_score']:.4f}), with mean normalized score {overall['mean_norm']:.4f}."
    )
    lines.append("")
    lines.append("## Suggested Tables")
    lines.append("")
    lines.append(
        "- Table: `counts_summary.csv` -> report raw/no-self/pruned rows and retained percentages for each category."
    )
    lines.append(
        "- Table: `evaluation_summary.csv` -> report accuracy@k and average runtime per query."
    )
    lines.append(
        "- Table: `transform_summary_pruned.csv` -> report transform frequency and share after pruning."
    )
    lines.append(
        "- Table: `score_summary_pruned.csv` -> report score and normalized-score distribution summaries."
    )
    lines.append("")
    lines.append("## Suggested Figures")
    lines.append("")
    lines.append(
        "- Figure: `accuracy_by_category_k.png` -> compare retrieval quality across domains and k."
    )
    lines.append(
        "- Figure: `pruning_funnel.png` -> visualize how filtering reduces result volume."
    )
    lines.append(
        "- Figure: `transform_share_heatmap.png` -> highlight which transforms drive most matches by category."
    )
    lines.append(
        "- Figure: `normalized_score_boxplot.png` -> compare confidence distributions across domains."
    )

    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    ensure_dirs()

    counts_df = load_counts()
    eval_df = load_eval_summary()
    pruned_df = load_pruned_rows()
    transform_df = load_transform_summary(pruned_df)
    score_df = load_score_summary(pruned_df)

    counts_df.to_csv(TABLE_DIR / "counts_summary.csv", index=False, quoting=csv.QUOTE_MINIMAL)
    eval_df.to_csv(TABLE_DIR / "evaluation_summary.csv", index=False, quoting=csv.QUOTE_MINIMAL)
    transform_df.to_csv(TABLE_DIR / "transform_summary_pruned.csv", index=False, quoting=csv.QUOTE_MINIMAL)
    score_df.to_csv(TABLE_DIR / "score_summary_pruned.csv", index=False, quoting=csv.QUOTE_MINIMAL)

    plot_accuracy(eval_df)
    plot_pruning_funnel(counts_df)
    plot_transform_heatmap(transform_df)
    plot_norm_box(pruned_df)

    write_markdown_summary(counts_df, eval_df, transform_df, score_df)
    write_dissertation_template(counts_df, eval_df, transform_df, score_df)

    print(f"Wrote tables to: {TABLE_DIR}")
    print(f"Wrote figures to: {FIG_DIR}")
    print(f"Wrote narrative summary to: {OUT_DIR / 'results_summary.md'}")
    print(f"Wrote dissertation template to: {OUT_DIR / 'dissertation_template.md'}")


if __name__ == "__main__":
    main()
