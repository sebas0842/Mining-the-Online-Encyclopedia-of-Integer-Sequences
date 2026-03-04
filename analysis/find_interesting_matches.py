from __future__ import annotations

import csv
import math
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
TESTS_DIR = ROOT / "tests"
OUT_DIR = ROOT / "analysis" / "output" / "interesting"


CATEGORY_CONFIG = [
    ("random", "random", "random"),
    ("polynomial", "polynomial", "poly"),
    ("prime", "prime", "prime"),
    ("combinatorics", "combinatronics", "combo"),
    ("graph_lattice_path", "graph:lattice:path", "graph"),
    ("all_500", "500_queries", "500"),
]


TRANSFORM_WEIGHT: Dict[str, float] = {
    "original": 2.8,
    "first_difference": 2.3,
    "cumulative_sum": 2.1,
    "reversal": 1.6,
    "shift_left_1": 1.2,
    "shift_left_2": 1.0,
    "shift_left_3": 0.8,
    "modulo_2": 0.35,
    "modulo_3": 0.55,
    "modulo_5": 0.75,
    "modulo_10": 0.45,
}


GENERIC_IDS = {
    "A000004",  # zero sequence
    "A000007",  # characteristic function of 0
    "A000012",  # all 1's
}


GENERIC_NAME_HINTS = [
    "zero sequence",
    "all 1",
    "all 0",
    "constant",
    "characteristic function",
    "mod ",
    "modulo",
    "inverse of",
    "cyclotomic",
]

KNOWN_RELATION_HINTS = [
    "partial sums of",
    "binomial transform of",
    "inverse of",
    "expansion of",
    "decimal expansion of",
    "characteristic sequence",
    "restricted growth sequence transform of",
    "transform of",
]


TOPIC_KEYWORDS: Dict[str, List[str]] = {
    "prime": ["prime", "primes", "goldbach"],
    "polynomial": ["polynomial", "coefficients", "g.f.", "generating function"],
    "combinatorics": ["partition", "catalan", "binomial", "stirling", "permutation", "combin"],
    "graph": ["graph", "lattice", "walk", "path", "tree", "network"],
    "number_theory": ["divisor", "totient", "congruent", "mod", "residue", "gcd"],
}


def ensure_dirs() -> None:

    OUT_DIR.mkdir(parents=True, exist_ok=True)


def load_pruned() -> pd.DataFrame:

    dfs: List[pd.DataFrame] = []

    for label, folder, prefix in CATEGORY_CONFIG:

        p = TESTS_DIR / folder / f"report_{prefix}_pruned.csv"
        df = pd.read_csv(p)
        df["category"] = label
        dfs.append(df)

    out = pd.concat(dfs, ignore_index=True)
    out["score"] = pd.to_numeric(out["score"], errors="coerce").fillna(0).astype(int)
    out["normalized_score"] = pd.to_numeric(out["normalized_score"], errors="coerce").fillna(0.0)
    return out


def detect_topics(name: str) -> List[str]:

    s = (name or "").lower()
    found: List[str] = []

    for topic, kws in TOPIC_KEYWORDS.items():

        if any(k in s for k in kws):

            found.append(topic)
    return found


def name_is_generic(name: str) -> bool:

    s = (name or "").lower()
    return any(h in s for h in GENERIC_NAME_HINTS)


def score_row(

    row: pd.Series,
    matched_freq: Dict[str, int],
    matched_category_count: Dict[str, int],
    pair_freq: Dict[Tuple[str, str], int],

) -> Tuple[float, str]:
    qid = row["query_id"]
    mid = row["matched_id"]
    transform = row["transform"]
    score = int(row["score"])
    norm = float(row["normalized_score"])
    qname = str(row.get("query_name", ""))
    mname = str(row.get("matched_name", ""))

    val = 0.0
    reasons: List[str] = []

    # strength terms
    val += 0.7 * score
    val += 12.0 * norm
    reasons.append(f"strength(score={score}, norm = {norm:.3f})")

    # transform informativeness
    tw = TRANSFORM_WEIGHT.get(transform, 0.8)
    val += tw
    reasons.append(f"transform = {transform}(+{tw:.2f})")

    # novelty: downweight frequent hubs
    f = matched_freq.get(mid, 1)
    novelty = 3.2 / (1.0 + math.log1p(float(f)))
    val += novelty
    reasons.append(f"rarity(mid_freq = {f}, +{novelty:.2f})")

    # reward matches repeated in more than one category

    ccount = matched_category_count.get(mid, 1)
    robust = min(float(ccount), 3.0) * 0.4
    val += robust
    reasons.append(f"cross_category(mid_categories = {ccount}, +{robust:.2f})")

    # penalise generic baseline targets

    if mid in GENERIC_IDS:

        val -= 4.0
        reasons.append("generic_id_penalty(-4.00)")

    if name_is_generic(mname):

        val -= 1.2
        reasons.append("generic_name_penalty(-1.20)")

    # penalise super-common pair repeats
    pf = pair_freq.get((qid, mid), 1)

    if pf > 1:

        penalty = min((pf - 1) * 0.5, 2.0)
        val -= penalty
        reasons.append(f"duplicate_pair(freq={pf}, -{penalty:.2f})")

    # penalise explicit known-link references
    qid_lower = qid.lower()
    mid_lower = mid.lower()
    qname_lower = qname.lower()
    mname_lower = mname.lower()

    if qid_lower in mname_lower or mid_lower in qname_lower:

        val -= 3.5
        reasons.append("explicit_cross_ref_penalty(-3.50)")

    if any(h in mname_lower for h in KNOWN_RELATION_HINTS):

        val -= 1.8
        reasons.append("known_relation_phrase_penalty(-1.80)")

    # semantic novelty reward: weaker overlap can indicate surprising links
    qt = set(detect_topics(qname))
    mt = set(detect_topics(mname))

    if qt and mt and not (qt & mt):

        bonus = 1.2 if transform in {"original", "first_difference", "cumulative_sum"} else 0.5
        val += bonus
        reasons.append(f"cross_topic(+{bonus:.2f})")

    # modulo-only exact matches are often arithmetically trivial

    if transform.startswith("modulo_") and norm >= 0.95:

        val -= 1.0
        reasons.append("trivial_mod_exact_penalty(-1.00)")

    return val, "; ".join(reasons)


def build_shortlist(df: pd.DataFrame) -> pd.DataFrame:

    matched_freq = df["matched_id"].value_counts().to_dict()
    matched_category_count = (
        df.groupby("matched_id")["category"].nunique().astype(int).to_dict()
    )
    pair_freq = (
        df.groupby(["query_id", "matched_id"]).size().astype(int).to_dict()
    )

    scores: List[float] = []
    reasons: List[str] = []

    for _, row in df.iterrows():

        s, r = score_row(row, matched_freq, matched_category_count, pair_freq)
        scores.append(s)
        reasons.append(r)
    out = df.copy()
    out["interestingness"] = scores
    out["reason"] = reasons

    # keep at most 2 matches per query
    out = out.sort_values(["query_id", "interestingness"], ascending=[True, False])
    out["query_rank"] = out.groupby("query_id").cumcount() + 1
    out = out[out["query_rank"] <= 2].copy()

    # final ordering
    out = out.sort_values("interestingness", ascending=False).reset_index(drop=True)
    return out


def write_outputs(shortlist: pd.DataFrame) -> None:

    short_all = shortlist.head(200).copy()
    short_all.to_csv(OUT_DIR / "interesting_matches_top200.csv", index=False, quoting=csv.QUOTE_MINIMAL)

    # Top 30 per category
    per_cat = (

        shortlist.groupby("category", group_keys=False)
        .head(30)
        .reset_index(drop=True)
    )
    per_cat.to_csv(OUT_DIR / "interesting_matches_top30_per_category.csv", index=False, quoting=csv.QUOTE_MINIMAL)

    # focused non-modulo shortlist for deeper mathematical follow-up
    non_mod = shortlist[~shortlist["transform"].str.startswith("modulo_")].copy()
    non_mod = non_mod.head(150)
    non_mod.to_csv(OUT_DIR / "interesting_non_modulo_top150.csv", index=False, quoting=csv.QUOTE_MINIMAL)

    # novelty-focused shortlist (exclude high-confidence trivial modulo and known-link language)
    novel = shortlist.copy()
    novel = novel[~novel["matched_id"].isin(GENERIC_IDS)]
    novel = novel[~novel["transform"].str.startswith("modulo_") | (novel["normalized_score"] < 0.95)]
    novel = novel[
        ~novel.apply(
            lambda r: (str(r["query_id"]).lower() in str(r["matched_name"]).lower())
            or (str(r["matched_id"]).lower() in str(r["query_name"]).lower()),
            axis=1,
        )
    ]
    novel = novel[
        ~novel["matched_name"].str.lower().str.contains(
            "|".join(KNOWN_RELATION_HINTS), regex=True
        )
    ]
    novel = novel.drop_duplicates(subset=["query_id", "matched_id", "transform"]).copy()
    novel = novel.sort_values("interestingness", ascending=False).head(120)
    novel.to_csv(OUT_DIR / "interesting_possibly_novel_top120.csv", index=False, quoting=csv.QUOTE_MINIMAL)

    # markdown digest
    lines: List[str] = []
    lines.append("# Interesting Match Candidates")
    lines.append("")
    lines.append("This file lists high-priority candidates for manual mathematical analysis.")
    lines.append("Scores are heuristic and designed to prioritize non-trivial, high-quality links.")
    lines.append("")

    for cat, g in per_cat.groupby("category"):

        lines.append(f"## {cat}")
        lines.append("")

        for _, r in g.head(10).iterrows():

            lines.append(
                f"- {r['query_id']} -> {r['matched_id']} | transform={r['transform']} | "
                f"score={int(r['score'])} | norm={float(r['normalized_score']):.3f} | "
                f"interestingness={float(r['interestingness']):.2f}\n"
                f"  - query: {r['query_name']}\n"
                f"  - matched: {r['matched_name']}"
            )
        lines.append("")

    (OUT_DIR / "interesting_matches_digest.md").write_text("\n".join(lines), encoding="utf-8")

    # novel digest
    nl: List[str] = []
    nl.append("# Possibly Novel Match Candidates")
    nl.append("")
    nl.append("Filtered to reduce likely-known/trivial relations.")
    nl.append("")

    for cat, g in novel.groupby("category"):

        nl.append(f"## {cat}")
        nl.append("")
        
        for _, r in g.head(10).iterrows():

            nl.append(
                f"- {r['query_id']} -> {r['matched_id']} | transform={r['transform']} | "
                f"score={int(r['score'])} | norm={float(r['normalized_score']):.3f} | "
                f"interestingness={float(r['interestingness']):.2f}\n"
                f"  - query: {r['query_name']}\n"
                f"  - matched: {r['matched_name']}"
            )
        nl.append("")
    (OUT_DIR / "interesting_possibly_novel_digest.md").write_text("\n".join(nl), encoding="utf-8")

    # Aggregate stats for writing
    stats = (
        shortlist.groupby("category")
        .agg(
            candidates=("query_id", "size"),
            mean_interestingness=("interestingness", "mean"),
            max_interestingness=("interestingness", "max"),
            non_modulo_share=("transform", lambda s: float((~s.str.startswith("modulo_")).mean())),
        )
        .reset_index()
    )
    stats["mean_interestingness"] = stats["mean_interestingness"].round(3)
    stats["max_interestingness"] = stats["max_interestingness"].round(3)
    stats["non_modulo_share"] = (100 * stats["non_modulo_share"]).round(2)
    stats.to_csv(OUT_DIR / "interestingness_stats.csv", index=False, quoting=csv.QUOTE_MINIMAL)


def main() -> None:
    ensure_dirs()
    df = load_pruned()
    shortlist = build_shortlist(df)
    write_outputs(shortlist)
    print(f"Wrote outputs to: {OUT_DIR}")
    print("Main files:")
    print("- interesting_matches_top200.csv")
    print("- interesting_matches_top30_per_category.csv")
    print("- interesting_non_modulo_top150.csv")
    print("- interesting_matches_digest.md")
    print("- interesting_possibly_novel_top120.csv")
    print("- interesting_possibly_novel_digest.md")
    print("- interestingness_stats.csv")


if __name__ == "__main__":
    main()
