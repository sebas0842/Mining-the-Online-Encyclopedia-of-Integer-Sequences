import re
from typing import List

_TERMS_RE = re.compile(r"\s*-?\d+(?:\s*,\s*-?\d+)*\s*$")

def is_valid_terms(s: str) -> bool:

    """Quick validation: only integers separated by commas (allow spaces)."""

    return bool(_TERMS_RE.fullmatch(s))

def normalize_terms(s: str) -> str:

    """
    Normalise by stripping spaces around commas and numbers.
    e.g. " 1,  2 ,3 " -> "1,2,3"

    """
    parts = [p.strip() for p in s.split(",")]

    # filter out accidental empty pieces; keep only integers-looking parts

    parts = [p for p in parts if p and (p == "0" or p.lstrip("-").isdigit())]
    return ",".join(parts)

def parse_terms(s: str) -> List[int]:

    """Convert a normalised comma string to a list of ints."""

    if not s:
        
        return []
    return [int(x) for x in s.split(",")]
