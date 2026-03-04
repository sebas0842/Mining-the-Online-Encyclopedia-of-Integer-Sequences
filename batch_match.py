from __future__ import annotations

import argparse
import csv
import sqlite3
from dataclasses import dataclass
from typing import Iterable, List, Optional, Tuple
from utils import parse_terms
from transform import apply_all_transformations


@dataclass  #simple data class to hold the results of a match operation

class BatchMatchRow:

    query_id: str
    query_name: str
    transform_name: str
    matched_id: str
    matched_name: str
    score: int
    normalized_score: float


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
        (seq_id,)
    ).fetchone()

    if row is None:

        raise ValueError(f"sequence ID not found: {seq_id}")

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
    Returns list of (matched_id, matched_name, score, normalized_score).
    """

    if not transformed_terms:

        return []

    prefix_n = min(prefix_n, len(transformed_terms))
    prefix_csv = csv_prefix(transformed_terms, prefix_n)

    if not prefix_csv:
        return []

    candidates = fetch_candidates_by_prefix(conn, prefix_csv, candidate_limit)

    scored: List[Tuple[str, str, int, float]] = []
    denom = float(len(transformed_terms))

    for cid, cname, cterms_csv in candidates:
        cterms = parse_terms(cterms_csv)
        score = longest_common_prefix_length(transformed_terms, cterms)

        if score > 0:

            scored.append((cid, cname, score, score / denom))

    scored.sort(key=lambda t: (-t[2], -t[3], t[0]))  # score desc, normalized desc, id asc
    return scored[:topk]


def iter_query_ids(path: str) -> Iterable[str]:

    with open(path, "r", encoding="utf-8", errors="replace") as f:

        for raw in f:

            s = raw.strip()
            if not s or s.startswith("#"):
                continue
            yield s


def run_batch(

    db_path: str,
    queries_path: str,
    out_csv: str,
    use_first_k: Optional[int],
    prefix_n: int,
    topk: int,
    candidate_limit: int,
    max_shift: int,
    modulo_values: List[int],
    min_score: int,
    min_normalized: float,
    exclude_self: bool
) -> None:
    conn = sqlite3.connect(db_path)

    try:

        with open(out_csv, "w", newline="", encoding="utf-8") as out_f:
            writer = csv.writer(out_f)
            writer.writerow([
                "query_id",
                "query_name",
                "transform",
                "matched_id",
                "matched_name",
                "score",
                "normalized_score"
            ])

            total_queries = 0
            total_rows = 0

            for qid in iter_query_ids(queries_path):
                total_queries += 1

                try:

                    sid, sname, sterms_csv = fetch_sequence(conn, qid)

                except Exception as e:

                    writer.writerow([qid, "", "ERROR", "", str(e), 0, 0.0])
                    continue

                terms = parse_terms(sterms_csv)
                if use_first_k is not None and use_first_k > 0:
                    terms = terms[:use_first_k]

                transforms = apply_all_transformations(

                    terms,
                    max_shift=max_shift,
                    modulo_values=modulo_values
                )

                for tr in transforms:

                    matches = match_transformation(

                        conn=conn,
                        transformed_terms=tr.terms,
                        prefix_n=prefix_n,
                        candidate_limit=candidate_limit,
                        topk=topk

                    )

                    for mid, mname, score, nscore in matches:
                        
                        if exclude_self and mid == sid:
                            continue
                        if score < min_score:
                            continue
                        if nscore < min_normalized:
                            continue

                        writer.writerow([sid, sname, tr.name, mid, mname, score, f"{nscore:.6f}"])
                        total_rows += 1

            print(f"Batch complete: {total_queries} queries processed")
            print(f"Report written: {out_csv}")
            print(f"Total match rows written: {total_rows}")

    finally:

        conn.close()


def main():

    ap = argparse.ArgumentParser(description="batch mining: run match pipeline for many OEIS IDs and write report.csv")
    ap.add_argument("--db", default="data/oeis.db", help="Path to SQLite database")
    ap.add_argument("--queries", required=True, help="Text file with query OEIS IDs (one per line)")
    ap.add_argument("--out", default="report.csv", help="Output CSV path")

    ap.add_argument("--use-first-k", type=int, default=None, help="Use only first k terms from each query sequence")
    ap.add_argument("--prefix-n", type=int, default=10, help="Prefix length used for candidate search")
    ap.add_argument("--topk", type=int, default=5, help="Top-k matches kept per transformation")
    ap.add_argument("--candidate-limit", type=int, default=200, help="Max candidate sequences per transformation")

    ap.add_argument("--max-shift", type=int, default=3, help="Max shift for shift transformations")
    ap.add_argument("--modulo-values", type=int, nargs="*", default=[2, 3, 5, 10], help="Modulo values for modulo transforms")

    ap.add_argument("--min-score", type=int, default=0, help="Only keep matches with score >= this value.")

    ap.add_argument("--min-normalized", type=float, default=0.0, help="Only keep matches with normalized_score >= this value.")

    ap.add_argument("--exclude-self", action="store_true", help="Exclude matches where matched_id == query_id.")

    args = ap.parse_args()

    run_batch(
        db_path=args.db,
        queries_path=args.queries,
        out_csv=args.out,
        use_first_k=args.use_first_k,
        prefix_n=args.prefix_n,
        topk=args.topk,
        candidate_limit=args.candidate_limit,
        max_shift=args.max_shift,
        modulo_values=args.modulo_values,
        min_score=args.min_score,
        min_normalized=args.min_normalized,
        exclude_self=args.exclude_self
    )


if __name__ == "__main__":
    main()