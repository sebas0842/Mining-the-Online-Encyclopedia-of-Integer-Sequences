import sqlite3
from database import get_sequence, find_by_terms_prefix

# Connect to local OEIS database
conn = sqlite3.connect("data/oeis.db")

# example 1: fetch specific sequence by ID (Fibonacci)
seq = get_sequence(conn, "A000045")
print("Single sequence lookup (A000045):")
print(seq)
print()

# 2xample 2: find sequences that start with 0,1,1 (Fibonacci like patterns)

matches = find_by_terms_prefix(conn, "0,1,1", limit=5)
print("Sequences starting with 0,1,1:")
for m in matches:
    print(m)

conn.close()
