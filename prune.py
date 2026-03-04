from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from typing import Dict, List, Tuple


def load_rows(path: str) -> Tuple[List[Dict[str, str]], List[str]]:

    with open(path, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        fieldnames = r.fieldnames or []
        rows = list(r)
    return rows, fieldnames


def save_rows(path: str, fieldnames: List[str], rows: List[Dict[str, str]]) -> None:

    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def to_int(x: str, default: int = 0) -> int:

    try:
        return int(x)
    except Exception:
        return default


def to_float(x: str, default: float = 0.0) -> float:

    try:
        return float(x)
    except Exception:
        return default


def remove_self(rows: List[Dict[str, str]]) -> List[Dict[str, str]]:

    out = []

    for row in rows:

        if row.get("query_id") == row.get("matched_id"):

            continue
        out.append(row)

    return out


def prune(

    rows: List[Dict[str, str]],
    min_score: int,
    min_norm: float,
    topn: int,
    per_transform: bool,
    exclude_transforms: List[str],
) -> List[Dict[str, str]]:

    # filter by thresholds + excluded transforms
    filtered = []
    excl = set(exclude_transforms)

    for row in rows:

        if row.get("transform", "") in excl:

            continue

        score = to_int(row.get("score", "0"))
        norm = to_float(row.get("normalized_score", "0"))

        if score < min_score:

            continue

        if norm < min_norm:

            continue
        filtered.append(row)


    groups: Dict[Tuple[str, str], List[Dict[str, str]]] = defaultdict(list)

    for row in filtered:

        qid = row.get("query_id", "")
        t = row.get("transform", "")
        key = (qid, t) if per_transform else (qid, "")
        groups[key].append(row)

    kept: List[Dict[str, str]] = []

    for _, grows in groups.items():

        grows.sort(

            key=lambda r: (

                -to_int(r.get("score", "0")),
                -to_float(r.get("normalized_score", "0")),
                r.get("matched_id", ""),
            )
        )
        kept.extend(grows[:topn])

    kept.sort(
        key=lambda r: (
            r.get("query_id", ""),
            r.get("transform", ""),
            -to_int(r.get("score", "0")),
            r.get("matched_id", ""),
        )
    )
    return kept


def main() -> None:

    ap = argparse.ArgumentParser(description="Prune batch mining CSV reports.")
    ap.add_argument("--in", dest="inp", required=True, help="Input CSV (raw)")
    ap.add_argument("--out-no-self", default="", help="Output CSV with self-matches removed")
    ap.add_argument("--out-pruned", default="", help="Output CSV pruned by thresholds + topN")

    ap.add_argument("--min-score", type=int, default=8, help="Minimum score to keep (default: 8)")
    ap.add_argument("--min-norm", type=float, default=0.20, help="Minimum normalized score (default: 0.20)")
    ap.add_argument("--topn", type=int, default=5, help="Keep top N per group (default: 5)")
    ap.add_argument(
        "--per-transform",
        action="store_true",
        help="Keep topN per (query_id, transform) instead of per query only",
    )
    ap.add_argument(
        "--exclude-transform",
        action="append",
        default=[],
        help="Exclude a transform (repeatable). Example: --exclude-transform original",
    )

    args = ap.parse_args()

    rows, fieldnames = load_rows(args.inp)

    if not rows:

        print(f"No rows in input: {args.inp}")

        if args.out_no_self:

            save_rows(args.out_no_self, fieldnames, [])

        if args.out_pruned:

            save_rows(args.out_pruned, fieldnames, [])
        return

    # step 1 --> remove self
    no_self = remove_self(rows)

    if args.out_no_self:

        save_rows(args.out_no_self, fieldnames, no_self)
        print(f"Wrote no-self report: {args.out_no_self} (rows={len(no_self)})")

    # step 2 --> prune by thresholds + topN

    pruned = prune(

        no_self,
        min_score=args.min_score,
        min_norm=args.min_norm,
        topn=args.topn,
        per_transform=args.per_transform,
        exclude_transforms=args.exclude_transform,
    )

    if args.out_pruned:

        save_rows(args.out_pruned, fieldnames, pruned)
        print(f"Wrote pruned report: {args.out_pruned} (rows={len(pruned)})")


if __name__ == "__main__":
    main()