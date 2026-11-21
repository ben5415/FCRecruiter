import re
from typing import Literal


RatingGrade = Literal["D", "C", "B", "A", "A+"]
_POSITION_RATING = re.compile(r"^\s*(\d+)(?:\s*([+-])\s*(\d+))?\s*$")


def rating_grade(value: int | float | None) -> RatingGrade | None:
    """Convert a 0-100 player rating to its public grade."""
    if value is None:
        return None
    if value < 50:
        return "D"
    if value < 65:
        return "C"
    if value < 75:
        return "B"
    if value < 85:
        return "A"
    return "A+"


def position_rating_grade(value: str | None) -> RatingGrade | None:
    """Grade FC position values such as ``86+3`` using their final value."""
    if value is None:
        return None
    match = _POSITION_RATING.fullmatch(value)
    if match is None:
        return None
    base = int(match.group(1))
    modifier = int(match.group(3) or 0)
    if match.group(2) == "-":
        modifier = -modifier
    return rating_grade(base + modifier)
