"""Convert Ten Thousand Tsumego JSON problems into SGF files.

The app bundled in this repository stores each problem as JSON::

    {"AB": ["eb", "fb"], "AW": ["da"], "SZ": "19", "C": "Black to play: Elementary",
     "SOL": [["B", "ba", "Correct.", ""], ["W", "", "", "warning text"]]}

``AB``/``AW`` are already SGF coordinates, ``SZ`` is the board size (int or string),
``C`` is the root comment and each ``SOL`` entry is ``[color, sgf_coordinate, comment, warning]``.
An empty coordinate is a pass. The corpus stores only alternative first moves of a single
color per problem, so all ``SOL`` entries are exported as sibling variations of the root.

Output is a standard FF[4] SGF game tree with provenance properties (``GN`` problem name,
``EV`` book, ``PC`` category, ``SO`` source file) and ``PL`` set to the color to play.
Text values are escaped per the FF[4] rules for ``]`` and ``\\``; newlines are kept literal,
which is how KaTrain (pysgf) expects them.

Use as a module or from the command line::

    python json_to_sgf.py [--problems-root problems] [--out sgf] [--mode problems|books|both]
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

CONVERTER_NAME = "tsumego-json-to-sgf"
CONVERTER_VERSION = "1.0"


class ProblemError(ValueError):
    """Raised for problem JSON that cannot be converted."""


def escape_sgf_value(text: str) -> str:
    """Escape a string for use as an SGF property value (FF[4] Text/SimpleText)."""
    return text.replace("\\", "\\\\").replace("]", "\\]")


def natural_key(text: str) -> list:
    """Sort key that orders embedded numbers numerically, like the app's natsorted listings."""
    return [(0, int(part)) if part.isdigit() else (1, part) for part in re.split(r"(\d+)", text)]


@dataclass(frozen=True)
class ProblemRef:
    """Location of one problem JSON file inside the problems tree.

    ``path`` is relative to the problems root so that ``source`` is portable.
    """

    category: str
    book: str
    stem: str
    path: Path

    @property
    def source(self) -> str:
        return self.path.as_posix()


def _parse_size(problem: dict) -> int:
    size = problem.get("SZ", 19)
    try:
        size = int(size)
    except (TypeError, ValueError):
        raise ProblemError(f"SZ is not an integer: {size!r}") from None
    if size < 1:
        raise ProblemError(f"SZ must be positive, got {size}")
    return size


def _validate_coord(coord, size: int, label: str, allow_empty: bool = False) -> str:
    if not isinstance(coord, str):
        raise ProblemError(f"{label} coordinate is not a string: {coord!r}")
    if coord == "":
        if allow_empty:
            return coord
        raise ProblemError(f"{label} coordinate is empty")
    if len(coord) != 2 or not all("a" <= ch <= chr(ord("a") + size - 1) for ch in coord):
        raise ProblemError(f"{label} coordinate {coord!r} is not on a {size}x{size} board")
    return coord


def _parse_stones(problem: dict, size: int, key: str) -> list[str]:
    stones = problem.get(key, [])
    if not isinstance(stones, list):
        raise ProblemError(f"{key} must be a list, got {type(stones).__name__}")
    return [_validate_coord(stone, size, key) for stone in stones]


def _parse_comment(problem: dict) -> str:
    comment = problem.get("C", "")
    if not isinstance(comment, str):
        raise ProblemError(f"C must be a string, got {type(comment).__name__}")
    return comment


def _parse_solutions(problem: dict, size: int) -> list[tuple[str, str, str, str]]:
    solutions = problem.get("SOL", [])
    if not isinstance(solutions, list):
        raise ProblemError(f"SOL must be a list, got {type(solutions).__name__}")
    parsed = []
    for i, entry in enumerate(solutions):
        if not isinstance(entry, list) or len(entry) < 2:
            raise ProblemError(f"SOL entry {i} must be [color, coordinate, ...], got {entry!r}")
        color, coord = entry[0], entry[1]
        if color not in ("B", "W"):
            raise ProblemError(f"SOL entry {i} has unknown color {color!r}")
        extra = [
            text if isinstance(text, str) else ""
            for text in entry[2:4]
        ]
        while len(extra) < 2:
            extra.append("")
        parsed.append((color, _validate_coord(coord, size, f"SOL entry {i}", allow_empty=True), extra[0], extra[1]))
    return parsed


def problem_to_sgf(problem: dict, *, name: str = "", book: str = "", category: str = "", source: str = "") -> str:
    """Convert one problem JSON dict into an FF[4] SGF game tree string.

    All ``SOL`` entries become sibling variations of the root, in order. Raises
    :class:`ProblemError` if the problem does not match the expected format.
    """
    size = _parse_size(problem)
    ab = _parse_stones(problem, size, "AB")
    aw = _parse_stones(problem, size, "AW")
    comment = _parse_comment(problem)
    solutions = _parse_solutions(problem, size)

    root: list[tuple[str, list[str]]] = [
        ("GM", ["1"]),
        ("FF", ["4"]),
        ("CA", ["UTF-8"]),
        ("AP", [f"{CONVERTER_NAME}:{CONVERTER_VERSION}"]),
        ("SZ", [str(size)]),
    ]
    if name:
        root.append(("GN", [name]))
    if book:
        root.append(("EV", [book]))
    if category:
        root.append(("PC", [category]))
    if source:
        root.append(("SO", [source]))
    if solutions:
        root.append(("PL", [solutions[0][0]]))
    if ab:
        root.append(("AB", ab))
    if aw:
        root.append(("AW", aw))
    if comment:
        root.append(("C", [comment]))

    children = []
    for i, (color, coord, sol_comment, warning) in enumerate(solutions):
        lines = [f"Solution {i + 1}: {coord if coord else 'pass'}"]
        if sol_comment:
            lines.append(sol_comment)
        if warning:
            lines.append(warning)
        children.append(_serialize_node([(color, [coord]), ("C", ["\n".join(lines)])], []))
    return _serialize_node(root, children)


def _serialize_node(properties: list[tuple[str, list[str]]], children: list[str]) -> str:
    parts = ["(", ";"]
    for key, values in properties:
        if values:
            parts.append(key + "".join(f"[{escape_sgf_value(value)}]" for value in values))
    for child in children:
        parts.append(child)
    parts.append(")")
    return "".join(parts)


def find_problem_files(root) -> list[ProblemRef]:
    """Find all problem JSON files under *root*, in natural path order."""
    root = Path(root)
    refs = []
    for path in sorted(root.rglob("*.json"), key=lambda p: natural_key(p.relative_to(root).as_posix())):
        relpath = path.relative_to(root)
        parts = relpath.parts
        category = parts[0] if len(parts) > 1 else ""
        book = "/".join(parts[1:-1])
        refs.append(ProblemRef(category=category, book=book, stem=path.stem, path=relpath))
    return refs
