"""Round-trip validation: convert the entire bundled corpus and re-parse every emitted
SGF with pysgf (the parser KaTrain itself uses), requiring exact agreement with the
source JSON for SZ, AB, AW, C, and all SOL data."""

import json
from pathlib import Path

import pytest

import pysgf

from json_to_sgf import export_problems, find_problem_files

REPO_ROOT = Path(__file__).resolve().parent.parent
PROBLEMS_ROOT = REPO_ROOT / "problems"
EXPECTED_PROBLEMS = 12640
EXPECTED_BOOKS = 55

if not PROBLEMS_ROOT.is_dir():
    pytest.skip("problem corpus not present", allow_module_level=True)


@pytest.fixture(scope="module")
def corpus_export(tmp_path_factory):
    out = tmp_path_factory.mktemp("sgf_corpus")
    stats = export_problems(PROBLEMS_ROOT, out, mode="both")
    return out, stats


def load_source(ref):
    return json.loads((PROBLEMS_ROOT / ref.path).read_text(encoding="utf-8"))


def source_text(text):
    """Source strings as a reader sees them: CR/CRLF normalized to newlines."""
    return text.replace("\r\n", "\n").replace("\r", "\n")


def source_size(problem):
    return int(problem.get("SZ", 19))


def exported_coord(coord, size):
    return "" if coord == "zz" and size < 26 else coord


def assert_solution_data_matches(child, entry, index, size):
    color, coord = entry[0], entry[1]
    comment = source_text(entry[2]) if len(entry) > 2 else ""
    warning = source_text(entry[3]) if len(entry) > 3 else ""
    assert child.get_property(color) == exported_coord(coord, size)
    child_comment = child.get_property("C")
    assert child_comment.startswith(f"Solution {index + 1}")
    if comment:
        assert comment in child_comment
    if warning:
        assert warning in child_comment
    if coord == "zz":
        assert "off-board" in child_comment


class TestCorpusRoundTrip:
    def test_every_problem_is_converted(self, corpus_export):
        out, stats = corpus_export
        assert stats.converted == EXPECTED_PROBLEMS
        assert stats.rejected == []
        assert stats.book_errors == []
        assert len(stats.written) == EXPECTED_PROBLEMS + EXPECTED_BOOKS

    def test_problem_files_match_source_json_exactly(self, corpus_export):
        out, _ = corpus_export
        for ref in find_problem_files(PROBLEMS_ROOT):
            problem = load_source(ref)
            size = source_size(problem)
            sgf_path = out / ref.category / ref.book / f"{ref.stem}.sgf"
            root = pysgf.GoGame(sgf_path.read_text(encoding="utf-8")).root
            assert root.get_property("SZ") == str(size), ref.source
            assert root.get_list_property("AB", []) == problem.get("AB", []), ref.source
            assert root.get_list_property("AW", []) == problem.get("AW", []), ref.source
            if problem.get("C"):
                assert root.get_property("C") == source_text(problem["C"]), ref.source
            assert root.get_property("GN") == ref.stem, ref.source
            assert root.get_property("EV") == ref.book, ref.source
            assert root.get_property("PC") == ref.category, ref.source
            assert root.get_property("SO") == ref.source, ref.source
            solutions = problem.get("SOL", [])
            if solutions:
                assert root.get_property("PL") == solutions[0][0], ref.source
            assert len(root.children) == len(solutions), ref.source
            for i, entry in enumerate(solutions):
                assert_solution_data_matches(root.children[i], entry, i, size)

    def test_book_files_contain_every_problem_as_a_branch(self, corpus_export):
        out, _ = corpus_export
        books = {}
        for ref in find_problem_files(PROBLEMS_ROOT):
            books.setdefault((ref.category, ref.book), []).append(ref)
        assert len(books) == EXPECTED_BOOKS
        for (category, book), refs in books.items():
            root = pysgf.GoGame((out / category / f"{book}.sgf").read_text(encoding="utf-8")).root
            assert root.get_property("EV") == book, book
            assert root.get_property("PC") == category, book
            assert len(root.children) == len(refs), book
            for ref, branch in zip(refs, root.children):
                problem = load_source(ref)
                size = source_size(problem)
                assert branch.get_list_property("AB", []) == problem.get("AB", []), ref.source
                assert branch.get_list_property("AW", []) == problem.get("AW", []), ref.source
                assert branch.get_property("C").startswith(ref.stem), ref.source
                if problem.get("C"):
                    assert source_text(problem["C"]) in branch.get_property("C"), ref.source
                solutions = problem.get("SOL", [])
                assert len(branch.children) == len(solutions), ref.source
                for i, entry in enumerate(solutions):
                    assert_solution_data_matches(branch.children[i], entry, i, size)

    def test_multi_solution_problems_are_sibling_variations(self, corpus_export):
        out, _ = corpus_export
        multi = [
            ref
            for ref in find_problem_files(PROBLEMS_ROOT)
            if len(load_source(ref).get("SOL", [])) > 1
        ]
        assert len(multi) == 813
        checked = 0
        for ref in multi:
            root = pysgf.GoGame(
                (out / ref.category / ref.book / f"{ref.stem}.sgf").read_text(encoding="utf-8")
            ).root
            colors = {child.get_property("B") is not None for child in root.children}
            assert len(colors) == 1, f"mixed-color solutions in {ref.source}"
            checked += len(root.children)
        assert checked == 1937  # SOL entries inside multi-solution problems; 13750 across the whole corpus
