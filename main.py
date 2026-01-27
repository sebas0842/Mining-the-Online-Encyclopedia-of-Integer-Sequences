import argparse
import logging
from parser import parse_oeis_file
from database import init_db, insert_many_ignore

def build_database(input_path: str, db_path: str, commit_chunk: int, max_rows: int | None):

    logging.info("Opening database: %s", db_path)
    conn = init_db(db_path)

    buffer = []
    total = 0
    inserted_total = 0
    ignored_total = 0
    skipped = 0

    def on_skip(_ln, _seq_id, _payload):

        nonlocal skipped
        skipped += 1

    logging.info("Starting import from: %s", input_path)

    try:

        with conn:

            for seq_id, terms, name in parse_oeis_file(input_path, on_skip=on_skip):

                buffer.append((seq_id, name, terms))
                total += 1

                if len(buffer) >= commit_chunk:

                    stats = insert_many_ignore(conn, buffer)
                    inserted_total += stats["inserted"]
                    ignored_total += stats["ignored"]

                    logging.info(

                        "Committed chunk: attempted=%d, inserted=%d, ignored=%d (total=%d)",
                        stats["attempted"], stats["inserted"], stats["ignored"], total

                    )

                    buffer.clear()

                if max_rows is not None and total >= max_rows:

                    break

            if buffer:

                stats = insert_many_ignore(conn, buffer)
                inserted_total += stats["inserted"]
                ignored_total += stats["ignored"]
                logging.info(
                    "Committed final chunk: attempted=%d, inserted=%d, ignored=%d (total=%d)",
                    stats["attempted"], stats["inserted"], stats["ignored"], total

                )
                buffer.clear()

    finally:

        conn.close()

    logging.info(

        "Database build complete.\n  Total parsed: %d\n  Inserted: %d\n  Duplicates ignored: %d\n  Skipped bad lines: %d",
        total, inserted_total, ignored_total, skipped

    )

def main():

    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="stripped")
    ap.add_argument("--db", default="data/oeis.db")
    ap.add_argument("--max-rows", type=int, default=None)
    ap.add_argument("--commit-chunk", type=int, default=5000)
    ap.add_argument("--log-level", default="INFO")
    args = ap.parse_args()

    logging.basicConfig(

        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-8s | %(message)s",

    )

    build_database(args.input, args.db, args.commit_chunk, args.max_rows)

if __name__ == "__main__":

    main()
