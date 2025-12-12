from parser import parse_oeis_file
from database import init_db, insert_sequence

def build_database():

    conn = init_db()
    for seq_id, terms, name in parse_oeis_file("stripped"):
        insert_sequence(conn, seq_id, name, terms)

    print("Database successfully built")

if __name__ == "__main__":

    build_database()

