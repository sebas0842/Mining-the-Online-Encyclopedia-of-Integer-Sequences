from __future__ import annotations
from typing import Callable, Optional, List, Sequence
from utils import normalize_terms, parse_terms
from dataclasses import dataclass

@dataclass(frozen=True)
class TransformResult:

    """ Result of applying a transformation to a sequence """

    name: str
    terms: List[int]

def shift(seq: Sequence[int], n: int) -> List[int]:

    """ Shift sequence by n places (positive n shifts right, negative left) 

        if n > 0: drop the first n terms (shift left)
        if n < 0: prepend -n zeros (shift right) 
        if n == 0: unchanged

    """

    if n == 0:

        return list(seq)

    elif n > 0:

        return list(seq[n:])

    return [0] * (-n) + list(seq)

def first_difference(seq: Sequence[int]) -> List[int]:

    """ Compute the first difference of the sequence """

    if len(seq) < 2:

        return []

    return [seq[i+1] - seq[i] for i in range(len(seq)-1)]

def cumulative_sum(seq: Sequence[int]) -> List[int]:

    """ Compute the cumulative sum of the sequence 
    
        Example: [1,2,3] -> [1,3,6] (partial sums)

    """

    out: List[int] = []
    total = 0

    for x in seq:

        total += x
        out.append(total)

    return out

def reversal(seq: Sequence[int]) -> List[int]:

    """ Reverse the sequence 
    
        Example: [1,2,3] -> [3,2,1]
    
    """

    return list(reversed(seq))

# map of transformation names to functions

def modulo_map(seq: Sequence[int], mod: int) -> List[int]:

    """ Apply modulo operation to each term in the sequence 
    
        Example: seq=[5,10,15], mod=6 -> [5,4,3]
    
    """

    if mod <= 0:

        raise ValueError("Modulo must be a positive integer") # error handling
    return [x % mod for x in seq]


def ratio_or_quotient(seq: Sequence[int]) -> List[Optional[float]]:

    """ Compute the ratio (or quotient) of consecutive terms in the sequence 
    
        Example: [2,4,8] -> [None, 2.0, 2.0]

        NOTE: Returns floats and uses None for division by zero
        NOTE: Skips divisions where dominatoris 0
    
    """

    if len(seq) < 2:

        return []

    out: List[Optional[float]] = []
    
    for i in range(len(seq) - 1):

        denomi = seq[i]
        num = seq[i + 1]

        out.append(None if denomi == 0 else num / denomi)

    return out

def apply_all_transformations(

    seq_id: Sequence[int],
    max_shift: int = 3,
    modulo_values: Optional[List[int]] = None
) -> List[TransformResult]:

    """ Apply a list of transformations to a sequence given its terms as CSV string 
    
        - Shifts: shift left by 1..max_shift
        - Difference
        - Cumulative sum
        - Reversal
        - Modulo mapping for a few values
    
    """

    if modulo_values is None:
        
        modulo_values = [2, 3, 5, 10]

    results: List[TransformResult] = []

    # base sequence

    results.append(TransformResult(name="original", terms=list(seq_id)))

    # shifts
    for n in range(1, max_shift + 1):

        shifted = shift(seq_id, n)
        results.append(TransformResult(name=f"shift_left_{n}", terms=shifted))

    # core transformations

    results.append(TransformResult(name="first_difference", terms=first_difference(seq_id)))
    results.append(TransformResult(name="cumulative_sum", terms=cumulative_sum(seq_id)))
    results.append(TransformResult(name="reversal", terms=reversal(seq_id)))

    for mod in modulo_values:

        results.append(TransformResult(name=f"modulo_{mod}", terms=modulo_map(seq_id, mod)))

    return results


