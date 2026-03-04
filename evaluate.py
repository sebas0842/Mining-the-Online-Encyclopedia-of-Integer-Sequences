from __future__ import annotations

import argparse
import csv
import sqlite3
import time
from dataclasses import dataclass
from typing import Iterable, List, Optional, Tuple, Dict

from utils import parse_terms
from transform import apply_all_transformations


# DB helpers join metadata to get names along with terms for matching and evaluation

def fetch_sequence(conn: sqlite3.Connection, seq_id: str) -> Tuple[str, str, str]:

    """
    Returns (id, name, terms_csv) for seq_id.
    """
    
    cur = conn.cursor()
    row = cur.execute(
        """
        SELECT
            s.id,
            COALESCE(m.name, '') AS name,
            s.terms
        FROM sequences AS s
        LEFT JOIN metadata AS m
            ON m.id = s.id
        WHERE s.id = ?
        """,
        (seq_id.strip(),)
    ).fetchone()

    if row is None:

        raise ValueError(f"Sequence id not found: {seq_id}")

    return row[0], row[1] or "", row[2] or ""


def fetch_candidates_by_prefix(

    conn: sqlite3.Connection,
    prefix_csv: str,
    limit: int
) -> List[Tuple[str, str, str]]:

    """
    Returns list of (id, name, terms_csv) where terms start with prefix_csv.
    """

    cur = conn.cursor()
    like_pattern = prefix_csv + ",%"
    rows = cur.execute(
        """
        SELECT
            s.id,
            COALESCE(m.name, '') AS name,
            s.terms
        FROM sequences AS s
        LEFT JOIN metadata AS m
            ON m.id = s.id
        WHERE s.terms = ?
           OR s.terms LIKE ?
        LIMIT ?
        """,
        (prefix_csv, like_pattern, limit)
    ).fetchall()

    return [(r[0], r[1] or "", r[2] or "") for r in rows]


# matching utilities and evaluation logic

def csv_prefix(terms: List[int], n: int) -> str:

    n = min(n, len(terms))
    return ",".join(str(x) for x in terms[:n])


def longest_common_prefix_length(a: List[int], b: List[int]) -> int:

    m = min(len(a), len(b))
    i = 0
    while i < m and a[i] == b[i]:
        i += 1
    return i


def match_transformation(

    conn: sqlite3.Connection,
    transformed_terms: List[int],
    prefix_n: int,
    candidate_limit: int,
    topk: int
) -> List[Tuple[str, str, int, float]]:

    """
    Returns list of (matched_id, matched_name, score, normalized_score),
    sorted by best match.
    """
    if not transformed_terms:

        return []

    prefix_n = min(prefix_n, len(transformed_terms))

    prefix_csv = csv_prefix(transformed_terms, prefix_n)

    if not prefix_csv:

        return []

    candidates = fetch_candidates_by_prefix(conn, prefix_csv, candidate_limit)

    denom = float(len(transformed_terms))
    scored: List[Tuple[str, str, int, float]] = []

    for cid, cname, cterms_csv in candidates:

        cterms = parse_terms(cterms_csv)
        score = longest_common_prefix_length(transformed_terms, cterms)

        if score > 0:

            scored.append((cid, cname, score, score / denom))

    scored.sort(key=lambda t: (-t[2], -t[3], t[0]))
    return scored[:topk]


# evaluation logic 

def iter_query_ids(path: str) -> Iterable[str]:

    with open(path, "r", encoding="utf-8", errors="replace") as f:

        for raw in f:

            s = raw.strip()
            if not s or s.startswith("#"):
                continue
            yield s


@dataclass # EvalResult holds results for one query and one k
class EvalResult:

    query_id: str
    query_name: str
    k: int
    found: bool
    found_rank: int  # 1-based rank, or 0 if not found
    found_transform: str
    seconds: float


def evaluate_one(

    conn: sqlite3.Connection,
    query_id: str,
    use_first_k: Optional[int],
    prefix_n: int,
    topk: int,
    candidate_limit: int,
    max_shift: int,
    modulo_values: List[int],
    mode: str
) -> EvalResult:
    """
    mode:
      - "original": only evaluate the 'original' transform
      - "any": evaluate success if query_id appears in topk for ANY transform
    """
    t0 = time.perf_counter()

    sid, sname, sterms_csv = fetch_sequence(conn, query_id)

    terms = parse_terms(sterms_csv)

    if use_first_k is not None and use_first_k > 0:

        terms = terms[:use_first_k]

    transforms = apply_all_transformations(

        terms,
        max_shift=max_shift,
        modulo_values=modulo_values
    )

    # only keep original transform for evaluation
    if mode == "original":
        transforms = [tr for tr in transforms if tr.name == "original"]

    found = False
    found_rank = 0
    found_transform = ""

    for tr in transforms:

        matches = match_transformation(
            conn=conn,
            transformed_terms=tr.terms,
            prefix_n=prefix_n,
            candidate_limit=candidate_limit,
            topk=topk
        )

        for idx, (mid, _mname, _score, _nscore) in enumerate(matches, start=1):

            if mid == sid:
                found = True
                found_rank = idx
                found_transform = tr.name
                break

        if found and mode == "any":
            break

    t1 = time.perf_counter()
    return EvalResult(
        query_id=sid,
        query_name=sname,
        k=topk,
        found=found,
        found_rank=found_rank,
        found_transform=found_transform,
        seconds=(t1 - t0),
    )


def run_eval(

    db_path: str,
    queries_path: str,
    out_csv: str,
    use_first_k: Optional[int],
    prefix_n: int,
    topk_list: List[int],
    candidate_limit: int,
    max_shift: int,
    modulo_values: List[int],
    mode: str,
    max_queries: Optional[int]
) -> None:
    conn = sqlite3.connect(db_path)

    try:

        query_ids = list(iter_query_ids(queries_path))
        if max_queries is not None and max_queries > 0:
            query_ids = query_ids[:max_queries]

        # compute accuracy@k for each k in topk_list
        # run evaluation separately for each k to get per-query results for each k
        all_results: List[EvalResult] = []

        for k in topk_list:

            for qid in query_ids:

                try:

                    res = evaluate_one(
                        conn=conn,
                        query_id=qid,
                        use_first_k=use_first_k,
                        prefix_n=prefix_n,
                        topk=k,
                        candidate_limit=candidate_limit,
                        max_shift=max_shift,
                        modulo_values=modulo_values,
                        mode=mode
                    )

                    all_results.append(res)

                except Exception as e:

                    # Record failure as not found

                    all_results.append(EvalResult(

                        query_id=qid,
                        query_name="",
                        k=k,
                        found=False,
                        found_rank=0,
                        found_transform=f"ERROR: {e}",
                        seconds=0.0,
                    ))

        # write per-query results
        with open(out_csv, "w", newline="", encoding="utf-8") as f:

            w = csv.writer(f)
            w.writerow([
                "query_id",
                "query_name",
                "k",
                "found",
                "found_rank",
                "found_transform",
                "seconds"
            ])
            for r in all_results:

                w.writerow([
                    r.query_id,
                    r.query_name,
                    r.k,
                    int(r.found),
                    r.found_rank,
                    r.found_transform,
                    f"{r.seconds:.6f}"
                ])

        # print summary
        print(f"Evaluation complete. Results written to: {out_csv}")
        print(f"Mode: {mode}")
        print(f"Queries evaluated: {len(query_ids)}")

        if use_first_k:

            print(f"Using first K terms: {use_first_k}")
        print(f"Prefix_n: {prefix_n}, Candidate_limit: {candidate_limit}\n")

        # Accuracy and runtime per k

        for k in topk_list:

            subset = [r for r in all_results if r.k == k]
            ok = sum(1 for r in subset if r.found)
            total = len(subset)
            acc = (ok / total) if total else 0.0
            avg_t = sum(r.seconds for r in subset) / total if total else 0.0
            print(f"accuracy@{k}: {ok}/{total} = {acc:.3f} | avg_time/query = {avg_t:.4f}s")

    finally:

        conn.close()


def main():

    ap = argparse.ArgumentParser(description="Evaluate matching accuracy@k and runtime on a set of OEIS IDs.")
    ap.add_argument("--db", default="data/oeis.db", help="Path to SQLite database")
    ap.add_argument("--queries", required=True, help="Text file with query OEIS IDs (one per line)")
    ap.add_argument("--out", default="eval_results.csv", help="Output CSV path")

    ap.add_argument("--use-first-k", type=int, default=25, help="Use only first k terms from each query sequence")
    ap.add_argument("--prefix-n", type=int, default=6, help="Prefix length used for candidate search")
    ap.add_argument("--candidate-limit", type=int, default=200, help="Max candidates per transformation")

    ap.add_argument("--max-shift", type=int, default=3, help="Max shift for shift transformations")
    ap.add_argument("--modulo-values", type=int, nargs="*", default=[2, 3, 5, 10], help="Modulo values for modulo transforms")

    ap.add_argument(
        "--mode",
        choices=["original", "any"],
        default="original",
        help="original = evaluate only original transform; any = success if found in any transform"
    )

    ap.add_argument(
        "--topk",
        type=int,
        nargs="*",
        default=[1, 5, 10],
        help="List of k values to compute accuracy@k (e.g., --topk 1 5 10)"
    )

    ap.add_argument("--max-queries", type=int, default=None, help="Limit number of queries for quick runs")

    args = ap.parse_args()

    run_eval(
        
        db_path=args.db,
        queries_path=args.queries,
        out_csv=args.out,
        use_first_k=args.use_first_k,
        prefix_n=args.prefix_n,
        topk_list=args.topk,
        candidate_limit=args.candidate_limit,
        max_shift=args.max_shift,
        modulo_values=args.modulo_values,
        mode=args.mode,
        max_queries=args.max_queries,
    )


if __name__ == "__main__":
    main()