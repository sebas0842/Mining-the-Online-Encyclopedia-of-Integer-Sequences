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
