import sqlite3

def init_db(db_path="data/oeis.db"):

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sequences (
            id TEXT PRIMARY KEY,
            name TEXT,
            terms TEXT
        )
    """)
    conn.commit()
    return conn

def insert_sequence(conn, seq_id, name, terms):

    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO sequences (id, name, terms) VALUES (?, ?, ?)",
        (seq_id, name, terms)
    )
    conn.commit()

