Mining the Online Encyclopedia of Integer Sequences (OEIS)

Overview:

This project is focused on automatically discovering relationships between integer sequences in the
Online Encyclopedia of Integer Sequences (OEIS).

The system builds a local searchable OEIS database and applies a set of mathematical transformations to sequences in order to detect similarities and hidden structural relationships between them.

Unlike OEIS Superseeker (which is limited to single queries), this project aims to provide a modular, extensible pipeline for:

    Efficient ingestion of OEIS data

    ransformation-based sequence exploration

    Heuristic similarity matching

    Local, reproducible experimentation

This under-development tool allows you to:

    Parse OEIS sequence data from the stripped dataset

    Store sequences locally in an optimized SQLite database

    Apply mathematical transformations such as:

        Shift

        First difference

        Cumulative sum

        Reversal

        Modulo mappings

    Search for similar OEIS sequences using heuristic prefix matching

    Rank candidate matches using similarity scoring

This enables discovery of relationships such as:

"Sequence B is the difference of Sequence A"

"Sequence C is Fibonacci modulo 2"

"Sequence D is a shifted version of Sequence E"


Project Structure:

The project consists of the following files:

Parser.py -->	Reads OEIS stripped file and yields sequences

database.py -->	Handles SQLite schema and database operations

main.py	--> Builds the OEIS database (ingestion pipeline)

utils.py --> Utility functions for parsing and normalization

transform.py --> Implements mathematical transformations

match.py --> Core matching engine (thesis contribution)

check.py --> Quick sanity-check script for database validation

check_queries.py --> Small helper to test search functions

data/	Local database storage (ignored by Git)


Requirements for running:

Python 3.10+

No external dependencies required (standard library only)


Step 1:

To start the prgram, one must first ingest the OEIS dataset:

    "python main.py --input stripped --db data/oeis.db"

Step 2:

Afterward, one can run the matching engine:
    python match.py data/oeis.db A000045 --prefix-n 6 --topk 5 --candidate-limit 200

What This Command Does:

    Loads sequence A000045 (Fibonacci)

    Applies transformations

    Searches database for structurally similar sequences

    Returns top-ranked matches for each transformation

Step3:

Then, one can make a sanity check:

    "python check.py"

    "sqlite3 data/oeis.db "SELECT COUNT(*) FROM sequences;"


How matching system (match.py) works:

For each transformed sequence:

    Extract first N terms → candidate prefix

    Use SQL prefix filtering to reduce search space

    Compare candidates using longest common prefix

    Rank results using similarity score

This allows scalable discovery without implementing a brute-force comparison.


Quick test examples for transform.py:

Transform fibonacci sequence to find potential matches:

"""
python - <<'PY'
from transform import apply_all_transformations

fib = [0,1,1,2,3,5,8,13,21]
print("Fibonacci test")

for t in apply_all_transformations(fib):
    print(f"{t.name:18} -> {t.terms[:10]}")
PY
"""

Verify a first difference logic:

python - <<'PY'
from transform import first_difference

"""
seq = [10, 13, 20, 25]
print(first_difference(seq))
PY
"""

Test modulo behaviour:

"""
python - <<'PY'
from transform import modulo_map

print(modulo_map([5,10,15,20], 6))
PY
"""