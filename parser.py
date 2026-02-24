from typing import Iterator, Tuple, Optional, Callable
import logging
from utils import is_valid_terms, normalize_terms

def parse_oeis_file(

    filepath: str = "stripped",
    on_skip: Optional[Callable[[int, str, str], None]] = None
) -> Iterator[Tuple[str, str, str]]:


    """
    Parses OEIS stripped file. Yields (seq_id, terms_csv, name="").
    on_skip: optional callback called as on_skip(line_number, seq_id_or_empty, raw_line_or_terms)
    """

    with open(filepath, "r", encoding="utf-8") as f:

        for ln, raw in enumerate(f, start=1):

            line = raw.strip()

            if not line or not line.startswith("A"):

                if on_skip: on_skip(ln, "", raw)
                continue

            parts = line.split(" ", 1)

            if len(parts) < 2:

                logging.warning("Skipping malformed line %d (no space after ID): %r", ln, raw[:120])
                if on_skip: on_skip(ln, parts[0] if parts else "", raw)
                continue

            seq_id = parts[0].strip()
            terms = parts[1].strip()

            if not is_valid_terms(terms):

                normalized = normalize_terms(terms)

                if not is_valid_terms(normalized):
                    
                    logging.warning("Skipping invalid terms at line %d for %s: %r", ln, seq_id, terms[:120])
                    if on_skip: on_skip(ln, seq_id, terms)
                    
                    continue
                terms = normalized

            terms = normalize_terms(terms)
            yield seq_id, terms, ""