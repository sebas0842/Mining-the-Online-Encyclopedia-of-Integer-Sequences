from __future__ import annotations
import argparse
import sqlite3
from typing import List, Tuple, Optional
from utils import normalize_terms


def connect(db_path: str) -> sqlite3.Connection:

    return sqlite3.connect(db_path)


def fetch_by_id(conn: sqlite3.Connection, seq_id: str) -> Optional[Tuple[str, str, str]]:

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

        return None

    return row[0], row[1] or "", row[2] or ""


def search_prefix(conn: sqlite3.Connection, prefix_csv: str, limit: int) -> List[Tuple[str, str, str]]:

    """
    Finds sequences where terms start with prefix_csv.
    Example prefix_csv: "0,1,1"
    """
    prefix_csv = normalize_terms(prefix_csv)
    like_pattern = prefix_csv + ",%"

    cur = conn.cursor()
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


def search_contains(conn: sqlite3.Connection, subseq_csv: str, limit: int) -> List[Tuple[str, str, str]]:

    """
    Simple subsequence search using LIKE on the terms string.

    Example subseq_csv: "13,21,34"
    Will match terms containing "...13,21,34..." anywhere.

    Note: This is a *text* search; it’s a useful MVP but not a perfect
    "term-boundary-aware" algorithm yet.
    """
    subseq_csv = normalize_terms(subseq_csv)

    # Best-effort boundary handling:
    # - match at start: "subseq,%"
    # - match in middle: "%,subseq,%"
    # - match at end: "%,subseq"
    pat_start = subseq_csv + ",%"
    pat_mid = "%," + subseq_csv + ",%"
    pat_end = "%," + subseq_csv

    cur = conn.cursor()
    rows = cur.execute(
        """
        SELECT
            s.id,
            COALESCE(m.name, '') AS name,
            s.terms
        FROM sequences AS s
        LEFT JOIN metadata AS m
            ON m.id = s.id
        WHERE s.terms LIKE ?
           OR s.terms LIKE ?
           OR s.terms LIKE ?
        LIMIT ?
        """,
        (pat_start, pat_mid, pat_end, limit)
    ).fetchall()

    return [(r[0], r[1] or "", r[2] or "") for r in rows]


def preview_terms(terms_csv: str, n_chars: int = 120) -> str:

    if len(terms_csv) <= n_chars:
        return terms_csv
    return terms_csv[:n_chars] + "..."


def main():

    ap = argparse.ArgumentParser(description="Query the local OEIS SQLite database (no SQL needed).")
    ap.add_argument("--db", default="data/oeis.db", help="Path to SQLite database")

    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--id", dest="seq_id", help="Fetch a sequence by OEIS ID (e.g., A000045)")
    g.add_argument("--prefix", help="Find sequences whose terms start with this CSV prefix (e.g., 0,1,1)")
    g.add_argument("--contains", help="Find sequences whose terms contain this CSV subsequence (e.g., 13,21,34)")

    ap.add_argument("--limit", type=int, default=20, help="Max results for prefix/contains searches")
    ap.add_argument("--show-terms", action="store_true", help="Print full terms (otherwise prints preview)")

    args = ap.parse_args()

    conn = connect(args.db)

    try:
        if args.seq_id:
            row = fetch_by_id(conn, args.seq_id)
            if row is None:
                print(f"Not found: {args.seq_id}")
                return

            sid, name, terms = row
            print(f"{sid} | {name}")
            if args.show_terms:
                print(terms)
            else:
                print(preview_terms(terms))

        elif args.prefix:

            rows = search_prefix(conn, args.prefix, args.limit)
            print(f"Prefix search: {normalize_terms(args.prefix)}")
            print(f"Found: {len(rows)} (limit={args.limit})\n")

            for sid, name, terms in rows:
                print(f"{sid} | {name}")
                print("  " + (terms if args.show_terms else preview_terms(terms)))
                print()

        elif args.contains:

            rows = search_contains(conn, args.contains, args.limit)
            print(f"Contains search: {normalize_terms(args.contains)}")
            print(f"Found: {len(rows)} (limit={args.limit})\n")

            for sid, name, terms in rows:
                print(f"{sid} | {name}")
                print("  " + (terms if args.show_terms else preview_terms(terms)))
                print()

    finally:

        conn.close()


if __name__ == "__main__":
    main()