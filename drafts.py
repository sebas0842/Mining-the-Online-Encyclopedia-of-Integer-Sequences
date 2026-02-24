#first code submission for supervisor revision during week 3. Quick and basic implementation of the three modules required for the OEIS database project.
# function: to parse the stripped OEIS file, initialize the database, and build the database from the parsed data.
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



# database.py code

from parser import parse_oeis_file
from database import init_db, insert_sequence

def build_database():

    conn = init_db()
    for seq_id, terms, name in parse_oeis_file("stripped"):
        insert_sequence(conn, seq_id, name, terms)

    print("Database successfully built")

if __name__ == "__main__":

    build_database()


# main.py code

def parse_oeis_file(filepath="stripped"):

    """
    Parses stripped OEIS file.
    Each line has the format: Axxxxxx term1,term2,term3
    """
    with open(filepath, "r") as f:

        for line in f:

            line = line.strip()
            
            if not line or not line.startswith("A"):

                continue
            
            parts = line.split(" ", 1)
            if len(parts) < 2:

                continue

            seq_id = parts[0].strip()
            terms = parts[1].strip()
            yield seq_id, terms, ""

