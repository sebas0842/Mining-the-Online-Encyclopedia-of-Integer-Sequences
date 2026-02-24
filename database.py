import sqlite3
import os 
from typing import Iterable, Tuple, Optional, Iterator


def init_db(db_path="data/oeis.db") -> sqlite3.Connection:

    db_dir = os.path.dirname(db_path) or "."
    os.makedirs(db_dir, exist_ok=True)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sequences (
            id TEXT PRIMARY KEY,
            name TEXT,
            terms TEXT
        )
    """)

    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("PRAGMA synchronous=NORMAL;")
    cursor.execute("PRAGMA temp_store=MEMORY;")
    cursor.execute("PRAGMA cache_size=30000000000;")  # 30GB cache

    conn.commit()
    return conn

def insert_sequence(conn: sqlite3.Connection, seq_id: str, name: str, terms: str) -> None:

    conn.execute(

        "INSERT OR REPLACE INTO sequences (id, name, terms)",
        (seq_id, name, terms)   
    )

"""
def insert_many(conn: sqlite3.Connection, rows: Iterable[Tuple[str, str, str]]) -> None:

    conn.executemany(

        "INSERT OR REPLACE INTO sequences (id, name, terms)",
        rows,
    )
"""

def insert_many_ignore(conn: sqlite3.Connection, rows: Iterable[Tuple[str, str, str]]) -> dict:

    """
    Bulk insert with INSERT OR IGNORE so I can count duplicates.
    returns: {"attempted": int, "inserted": int, "ignored": int}

    """
    rows = list(rows)
    before = conn.total_changes

    conn.executemany(

        "INSERT OR IGNORE INTO sequences (id, name, terms)",
        rows,
    )

    delta = conn.total_changes - before  # number of rows actually inserted
    attempted = len(rows)
    return {"attempted": attempted, "inserted": delta, "ignored": attempted - delta}

# test helper code 

# Read helpers

def get_sequence(conn: sqlite3.Connection, seq_id: str) -> Optional[Tuple[str, str, str]]:

    """Fetch one sequence by id"""

    cur = conn.execute("SELECT id, name, terms FROM sequences WHERE id = ?", (seq_id,))
    return cur.fetchone()

def iter_sequences(conn: sqlite3.Connection, limit: int | None = None, offset: int = 0) -> Iterator[Tuple[str, str, str]]:

    """Iterate through sequences in database."""

    sql = "SELECT id, name, terms FROM sequences"
    params: tuple = ()

    if limit is not None:

        sql += " LIMIT ? OFFSET ?"
        params = (limit, offset)
    cur = conn.execute(sql, params)

    yield from cur

def find_by_terms_prefix(conn: sqlite3.Connection, prefix_csv: str, limit: int = 50) -> list[Tuple[str, str, str]]:

    """
    Search for sequences whose terms start with the given prefix.
    Example: prefix_csv="0,1,1" → returns Fibonacci and similar sequences.
    """

    like = prefix_csv + ",%"
    eq = prefix_csv
    cur = conn.execute(

        "SELECT id, name, terms FROM sequences WHERE terms = ? OR terms LIKE ? LIMIT ?",
        (eq, like, limit)
    )
    return cur.fetchall()