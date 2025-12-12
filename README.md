# OEIS Mining the OIES (Thesis)


This repository contains the current progress of my thesis project, which focuses on building a system to ingest, clean, store, and query integer sequences from the OEIS.

The goal of the project is to support large-scale analysis of integer sequences, including transformations and similarity detection between sequences.


## Current Features

- Parses the OEIS `stripped` dataset
- Cleans and normalizes sequence terms
- Stores sequences in a local SQLite database
- Fast ingestion using chunked transactions
- Handles duplicate entries safely
- Skips and logs malformed lines
- Basic search and query functionality
- Sanity-check and inspection scripts

## Project Structure

main.py # Database builder (ingestion pipeline)
parser.py # OEIS file parser and validator
database.py # SQLite setup and query helpers
utils.py # Term validation and normalization
check.py # Database health and sanity checks
check_queries.py # Example sequence queries
data/ # Local database
stripped # OEIS dataset


## Requirements

- Python 3.12+ (tested with 3.13)
- SQLite3 (included with macOS and most Linux systems)



