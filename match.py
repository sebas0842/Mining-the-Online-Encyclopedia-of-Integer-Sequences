from __future__ import annotations
import sqlite3
import argparse
from typing import List, Optional, Tuple
from utils import parse_terms
from transform import apply_all_transformations
from dataclasses import dataclass

try:
    from database import get_sequence

except Exception:

    get_sequence = None

@dataclass
class MatchResult:
    
    """ Result of a matching operation """

    seq_id: str
    name: str   
    score : int             # length of matched terms
    normalized_score: float # score / length of matched terms

def csv_prefix(terms: List[int], n: int) -> str:

    """ Return the first n terms as a CSV string (Comma-Separated Values). """

    n = min(n, len(terms))

    return ",".join(str(terms[i]) for i in range(min(n, len(terms))))

def fetch_sequence(conn: sqlite3.Connection, seq_id: str) -> Tuple[str, str, str]:

    """ Fetch sequence terms from the database by its ID """

    if get_sequence is not None:

        row = get_sequence(conn, seq_id)

        if row is None:

            raise ValueError(f"Sequence ID {seq_id} not found in the database")

        return row[0], row[1] or "", row[2]
    
    cur = conn.cursor() # cursor
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
        """, (seq_id,)

    ).fetchone()

    if row is None:

        raise ValueError(f"Sequence ID {seq_id} not found in the database")
    
    return row[0], row[1] or "", row[2] or ""


def fetch_candidate_sequences_by_prefix(

        conn: sqlite3.connection,
        prefix_csv: str,
        limit: int
        ) -> List[Tuple[str, str, str]]:

        """
        Return candidate rows (id, name, terms_csv) whose terms start with prefix_csv.
        """

        cur = conn.cursor()
        like_pattern = prefix_csv + ",%"  # SQL LIKE pattern

        rows = cur.execute(

            """
            SELECT 
                s.id,
                COALESCE(m.name, '') AS name,
                s.terms
            FROM sequences AS s
            LEFT JOIN metadata AS m ON s.id = m.id
            WHERE s.terms = ? OR s.terms LIKE ?
            LIMIT ?
            """, (prefix_csv, like_pattern, limit)

        ).fetchall()

        return [(row[0], row[1] or "", row[2] or "") for row in rows]


def longest_common_prefix_length(a : List[int], b: List[int]) -> int:

    """ Return the length of the longest common prefix of two sequences. """

    min_len = min(len(a), len(b))

    i = 0

    while i < min_len and a[i] == b[i]:
        
        i += 1
    return i

def match_one_transformation(

    conn: sqlite3.Connection,
    transformed_terms: List[int],
    prefix_n: int,
    candidate_limit: int,
    topk: int
    ) -> List[MatchResult]:

    """
    For a transformed sequence:
     find candidates using the first prefix_n terms
     score each candidate by longest common prefix length
     return topk matches as a list of tuples:
    """

    if not transformed_terms:

        return []
    
    # beuristic: limit prefix_n to length of transformed_terms

    prefix_n = min(prefix_n, len(transformed_terms))
    prefix_csv = csv_prefix(transformed_terms, prefix_n)

    if prefix_csv == "":

        return []
    
    candidates = fetch_candidate_sequences_by_prefix(conn, prefix_csv, candidate_limit)

    results: List[MatchResult] = []

    for cid, cname, cterms_csv in candidates:

        cterms = parse_terms(cterms_csv)

        score = longest_common_prefix_length(transformed_terms, cterms)

        if score > 0:
            normalized = score / len(transformed_terms)
            results.append(
                MatchResult(
                    
                    seq_id = cid,
                    name = cname,
                    score = score,
                    normalized_score = normalized
            ))

    results.sort(key = lambda r: (-r.score, -r.normalized_score, r.seq_id))
    return results[:topk]

def run_matching(
    db_path: str,
    seq_id: str,
    use_first_k: int,
    prefix_n: int,
    topk: int,
    candidate_limit: int,
    max_shift: int,
    modulo_values: List[int],

) -> None:

    conn = sqlite3.connect(db_path)

    try:

        sid, sname, sterms_csv = fetch_sequence(conn, seq_id)
        sterms = parse_terms(sterms_csv)

        if use_first_k is not None and use_first_k > 0:

            sterms = sterms[:use_first_k]

        print(f"Matching for Sequence ID: {sid}, Name: {sname}")
        print(f"Terms preview: {sterms_csv[:80]} {'...' if len(sterms_csv) > 80 else ''}\n")

        if sname:
            
            print(f"Name: {sname}")

        print(f"Using first {len(sterms)} terms: {','.join(str(t) for t in sterms)}")
        print(f" {sterms[:20]} {'...' if len(sterms) > 20 else ''}\n")

        transformations = apply_all_transformations(

            sterms,
            max_shift = max_shift,
            modulo_values = modulo_values
        )

        for transform in transformations:

            results = match_one_transformation(

                conn = conn,
                transformed_terms = transform.terms,
                prefix_n = prefix_n,
                candidate_limit = candidate_limit,
                topk = topk
            )

            preview = csv_prefix(transform.terms, min(10, len(transform.terms)))
            print(f"Transformation: {transform.name}, Terms Preview: {preview} {'...' if len(transform.terms) > 10 else ''}")
            print(f" Found {len(results)} matches:")


            if not results:
                
                print("  No matches found.")

                continue

            for r in results:

                print(f"  Match: ID ={r.seq_id}, Name ={r.name}, Score={r.score}, Normalized Score ={r.normalized_score}")

            print()

    finally:

        conn.close()

def main():

    ap = argparse.ArgumentParser(description="Match sequences in the database using transformations.")
    ap.add_argument("db_path", help = "Path to the SQLite database file.")
    ap.add_argument("seq_id", help = "Sequence ID to match.")
    ap.add_argument("--use-first-k", type = int, default = None, help = "Use only first k terms of the sequence for matching.")
    ap.add_argument("--prefix-n", type = int, default = 10, help = "Number of terms from the start of transformed sequence to use for candidate search.")
    ap.add_argument("--topk", type = int, default = 10, help = "Number of top matches to return per transformation.")
    ap.add_argument("--candidate-limit", type = int, default = 200, help = "Maximum number of candidate sequences to consider per transformation.")
    ap.add_argument("--max-shift", type = int, default = 3, help = "Maximum shift amount for shift transformations.")
    ap.add_argument("--modulo-values", type = int, nargs = "*", default = [2, 3, 5, 10], help = "List of modulo values for modulo transformations.")

    args = ap.parse_args()

    modulo_values = args.modulo_values

    run_matching(

        db_path = args.db_path,
        seq_id = args.seq_id,
        use_first_k = args.use_first_k,
        prefix_n = args.prefix_n,
        topk = args.topk,
        candidate_limit = args.candidate_limit,
        max_shift = args.max_shift,
        modulo_values = modulo_values

    )

if __name__ == "__main__":
    
    main()