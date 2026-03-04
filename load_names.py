import argparse
import sqlite3
from parser import parse_names_file
from database import init_metadata_table, upsert_names

def main():

    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="data/oeis.db")
    ap.add_argument("--names", default="names")
    ap.add_argument("--commit-chunk", type=int, default=5000)
    args = ap.parse_args()

    conn = sqlite3.connect(args.db)

    try:
        
        init_metadata_table(conn)

        buf = []
        total = 0

        for seq_id, name in parse_names_file(args.names):

            buf.append((seq_id, name))

            if len(buf) >= args.commit_chunk:

                upsert_names(conn, buf)
                conn.commit()
                total += len(buf)
                buf.clear()

                print(f"Loaded {total} names...")

        if buf:

            upsert_names(conn, buf)
            conn.commit()
            total += len(buf)

        print(f"Done. Loaded {total} names into metadata table.")
        
    finally:
        conn.close()

if __name__ == "__main__":
    main()