import argparse, sqlite3

def main(db: str, sample: int):

    conn = sqlite3.connect(db)
    cur = conn.cursor()
    total = cur.execute("SELECT COUNT(*) FROM sequences").fetchone()[0]

    print(f"Total sequences: {total}")
    print("\nSample rows:")

    for row in cur.execute("SELECT id, substr(terms,1,80)||'…' FROM sequences LIMIT ?", (sample,)):

        print("  ", row)

    print("\nFibonacci-like starts (0,1,1,…):")

    for row in cur.execute("SELECT id FROM sequences WHERE terms LIKE '0,1,1,%' LIMIT 10"):

        print("  ", row[0])

    conn.close()

if __name__ == "__main__":
    
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="data/oeis.db")
    ap.add_argument("--sample", type=int, default=5)
    args = ap.parse_args()
    main(args.db, args.sample)
