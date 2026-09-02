"""Convert Ten Thousand Tsumego JSON problems into SGF files.

The app bundled in this repository stores each problem as JSON::

    {"AB": ["eb", "fb"], "AW": ["da"], "SZ": "19", "C": "Black to play: Elementary",
     "SOL": [["B", "ba", "Correct.", ""], ["W", "", "", "warning text"]]}

``AB``/``AW`` are already SGF coordinates, ``SZ`` is the board size (int or string),
``C`` is the root comment and each ``SOL`` entry is ``[color, sgf_coordinate, comment, warning]``.
An empty coordinate is a pass. The corpus stores only alternative first moves of a single
color per problem, so all ``SOL`` entries are exported as sibling variations of the root.
The Go Seigen dictionary uses the off-board token ``"zz"`` for "no local move"; such
solutions are exported as a pass with a note naming the original coordinate.

Output is a standard FF[4] SGF game tree with provenance properties (``GN`` problem name,
``EV`` book, ``PC`` category, ``SO`` source file) and ``PL`` set to the color to play.
Text values are escaped per the FF[4] rules for ``]`` and ``\\``; newlines are kept literal,
which is how KaTrain (pysgf) expects them.

Use as a module or from the command line::

    python json_to_sgf.py [--problems-root problems] [--out sgf] [--mode problems|books|both]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
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
    if coord == "zz" and size < 26 and allow_empty:
        # The Go Seigen dictionary uses the off-board token "zz" for "no local move";
        # export it as a pass and keep the provenance in the variation comment.
        return ""
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


def _parse_solutions(problem: dict, size: int) -> list[tuple[str, str, str, str, str]]:
    """Parse SOL entries into ``(color, coord, comment, warning, note)`` tuples.

    ``note`` carries converter provenance, e.g. for solutions exported as a pass.
    """
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
        note = "source coordinate 'zz' is off-board; exported as pass" if coord == "zz" and size < 26 else ""
        extra = [
            text if isinstance(text, str) else ""
            for text in entry[2:4]
        ]
        while len(extra) < 2:
            extra.append("")
        parsed.append((color, _validate_coord(coord, size, f"SOL entry {i}", allow_empty=True), extra[0], extra[1], note))
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

    return _serialize_node(root, _solution_children(solutions))


def _solution_children(solutions: list[tuple[str, str, str, str, str]]) -> list[str]:
    """Serialize every solution as a sibling variation subtree, in corpus order."""
    children = []
    for i, (color, coord, sol_comment, warning, note) in enumerate(solutions):
        lines = [f"Solution {i + 1}: {coord if coord else 'pass'}"]
        if sol_comment:
            lines.append(sol_comment)
        if warning:
            lines.append(warning)
        if note:
            lines.append(note)
        children.append(_serialize_node([(color, [coord]), ("C", ["\n".join(lines)])], []))
    return children


def problem_branch(problem: dict, *, name: str = "", source: str = "") -> str:
    """Convert one problem into a setup branch for use inside a combined book SGF.

    The branch carries the problem's stones and comment; the problem name is prefixed
    to the comment so it stays visible while browsing a book in an SGF editor.
    """
    size = _parse_size(problem)
    ab = _parse_stones(problem, size, "AB")
    aw = _parse_stones(problem, size, "AW")
    comment = _parse_comment(problem)
    solutions = _parse_solutions(problem, size)

    branch: list[tuple[str, list[str]]] = []
    if ab:
        branch.append(("AB", ab))
    if aw:
        branch.append(("AW", aw))
    if solutions:
        branch.append(("PL", [solutions[0][0]]))
    branch.append(("C", [f"{name}\n\n{comment}" if comment else name]))
    return _serialize_node(branch, _solution_children(solutions))


def book_to_sgf(category: str, book: str, entries: list[tuple[ProblemRef, dict]]) -> str:
    """Convert a list of ``(ref, problem)`` pairs (one book) into a single-game SGF tree.

    Every problem becomes a sibling branch of the root, which keeps each problem's
    position reachable as a variation. All problems must share one board size.
    """
    problems = [problem for _, problem in entries]
    sizes = {_parse_size(problem) for problem in problems}
    if len(sizes) > 1:
        raise ProblemError(f"book mixes board sizes {sorted(sizes)}; export it per board size")
    size = sizes.pop()
    root: list[tuple[str, list[str]]] = [
        ("GM", ["1"]),
        ("FF", ["4"]),
        ("CA", ["UTF-8"]),
        ("AP", [f"{CONVERTER_NAME}:{CONVERTER_VERSION}"]),
        ("SZ", [str(size)]),
        ("PC", [category]),
        ("EV", [book]),
        (
            "C",
            [f"{book} ({category})\n{len(entries)} problems converted from JSON by {CONVERTER_NAME} {CONVERTER_VERSION}"],
        ),
    ]
    return _serialize_node(root, [problem_branch(problem, name=ref.stem) for ref, problem in entries])


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


@dataclass
class ExportStats:
    """Result of one export run."""

    converted: int = 0
    rejected: list[tuple[ProblemRef, str]] = field(default_factory=list)
    book_errors: list[str] = field(default_factory=list)
    written: list[Path] = field(default_factory=list)


def _load_problem(ref: ProblemRef, problems_root: Path) -> dict:
    try:
        return json.loads((problems_root / ref.path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as e:
        raise ProblemError(f"cannot read problem JSON: {e}") from None


def export_problems(problems_root, out_root, mode: str = "both") -> ExportStats:
    """Convert every problem under *problems_root* and write SGF files under *out_root*.

    Modes: ``problems`` writes one SGF file per problem (mirroring the source layout),
    ``books`` writes one combined SGF game per book, ``both`` writes both layouts.
    Files with unusable JSON are counted in :attr:`ExportStats.rejected` and skipped.
    """
    if mode not in ("problems", "books", "both"):
        raise ValueError(f"unknown mode {mode!r}")
    problems_root, out_root = Path(problems_root), Path(out_root)
    stats = ExportStats()
    by_book: dict[tuple[str, str], list[tuple[ProblemRef, dict]]] = defaultdict(list)

    for ref in find_problem_files(problems_root):
        try:
            problem = _load_problem(ref, problems_root)
            sgf = problem_to_sgf(problem, name=ref.stem, book=ref.book, category=ref.category, source=ref.source)
        except ProblemError as e:
            stats.rejected.append((ref, str(e)))
            continue
        stats.converted += 1
        by_book[(ref.category, ref.book)].append((ref, problem))
        if mode in ("problems", "both"):
            target = out_root / ref.category / ref.book / f"{ref.stem}.sgf"
            _write_sgf(target, sgf)
            stats.written.append(target)

    if mode in ("books", "both"):
        for (category, book), entries in by_book.items():
            try:
                book_sgf = book_to_sgf(category, book, entries)
            except ProblemError as e:
                stats.book_errors.append(f"{category}/{book}: {e}")
                continue
            target = out_root / category / f"{book}.sgf"
            _write_sgf(target, book_sgf)
            stats.written.append(target)
    return stats


def _write_sgf(target: Path, sgf: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(sgf + "\n", encoding="utf-8")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Convert Ten Thousand Tsumego JSON problems to KaTrain-compatible SGF files."
    )
    parser.add_argument("--problems-root", type=Path, default=Path("problems"), help="directory with the JSON problems")
    parser.add_argument("--out", type=Path, default=Path("sgf"), help="output directory for the SGF files")
    parser.add_argument(
        "--mode",
        choices=("problems", "books", "both"),
        default="both",
        help="export one file per problem, one combined file per book, or both (default)",
    )
    args = parser.parse_args(argv)

    stats = export_problems(args.problems_root, args.out, mode=args.mode)
    for ref, reason in stats.rejected:
        print(f"rejected {ref.source}: {reason}", file=sys.stderr)
    for error in stats.book_errors:
        print(f"book failed {error}", file=sys.stderr)
    print(
        f"Converted {stats.converted} problems ({len(stats.rejected)} rejected, "
        f"{len(stats.book_errors)} failed books), wrote {len(stats.written)} SGF files to {args.out}"
    )
    return 1 if stats.rejected or stats.book_errors else 0


if __name__ == "__main__":
    sys.exit(main())
