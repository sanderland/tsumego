import pytest

from json_to_sgf import (
    ProblemError,
    ProblemRef,
    escape_sgf_value,
    find_problem_files,
    natural_key,
    problem_to_sgf,
)


PROB0001 = {
    "AB": ["eb", "fb", "bc", "cc", "dc", "be"],
    "AW": ["da", "ab", "bb", "cb", "db"],
    "SZ": "19",
    "C": "Black to play: Elementary",
    "SOL": [["B", "ba", "Correct.", ""]],
}


def parse_tree(sgf):
    pysgf = pytest.importorskip("pysgf")
    return pysgf.GoGame(sgf).root


class TestEscape:
    def test_plain_text_unchanged(self):
        assert escape_sgf_value("Black to play") == "Black to play"

    def test_escapes_closing_bracket(self):
        assert escape_sgf_value("a]b") == "a\\]b"

    def test_escapes_backslash(self):
        assert escape_sgf_value("a\\b") == "a\\\\b"

    def test_escapes_backslash_before_bracket(self):
        assert escape_sgf_value("a\\]b") == "a\\\\\\]b"

    def test_keeps_newlines_literal(self):
        assert escape_sgf_value("one\ntwo") == "one\ntwo"


class TestProblemToSgf:
    def test_single_solution_problem(self):
        sgf = problem_to_sgf(PROB0001)
        root = parse_tree(sgf)
        assert root.get_list_property("AB") == PROB0001["AB"]
        assert root.get_list_property("AW") == PROB0001["AW"]
        assert root.get_property("SZ") == "19"
        assert root.get_property("C") == "Black to play: Elementary"
        assert root.get_property("PL") == "B"
        assert [child.get_property("B") for child in root.children] == ["ba"]

    def test_solution_node_comment(self):
        sgf = problem_to_sgf(PROB0001)
        root = parse_tree(sgf)
        assert root.children[0].get_property("C") == "Solution 1: ba\nCorrect."

    def test_multiple_solutions_become_siblings_in_order(self):
        problem = {
            "AB": ["ns"], "AW": [], "SZ": 19,
            "C": "White to play: Tesuji",
            "SOL": [
                ["B", "ns", "", "Backup solution detector used, solution may be incorrect."],
                ["B", "mr", "", "Backup solution detector used, solution may be incorrect."],
                ["B", "or", "", ""],
            ],
        }
        root = parse_tree(problem_to_sgf(problem))
        assert [child.get_property("B") for child in root.children] == ["ns", "mr", "or"]
        assert [child.get_property("W") for child in root.children] == [None, None, None]
        assert "Solution 2: mr" in root.children[1].get_property("C")
        assert "Backup solution detector used, solution may be incorrect." in root.children[0].get_property("C")
        assert "Backup" not in root.children[2].get_property("C")

    def test_pass_solution(self):
        problem = {"AB": ["aa"], "AW": ["bb"], "SZ": 19, "SOL": [["W", "", "", "no move needed"]]}
        root = parse_tree(problem_to_sgf(problem))
        assert root.get_property("PL") == "W"
        assert root.children[0].get_property("W") == ""
        assert root.children[0].get_property("C") == "Solution 1: pass\nno move needed"

    def test_sz_accepts_int_and_string(self):
        assert 'SZ[19]' in problem_to_sgf({"SZ": 19, "SOL": []})
        assert 'SZ[13]' in problem_to_sgf({"SZ": "13", "SOL": []})

    def test_board_size_bounds_coordinates(self):
        problem = {"AB": ["sa"], "SZ": 19, "SOL": [["B", "ss"]]}
        assert 'AB[sa]' in problem_to_sgf(problem)
        with pytest.raises(ProblemError):
            problem_to_sgf({"AB": ["ta"], "SZ": 19, "SOL": []})
        with pytest.raises(ProblemError):
            problem_to_sgf({"AB": ["aa"], "SZ": 19, "SOL": [["B", "st"]]})

    def test_metadata_properties(self):
        sgf = problem_to_sgf(PROB0001, name="Prob0001", book="Cho Chikun Elementary", category="1a. Tsumego Beginner",
                             source="problems/1a. Tsumego Beginner/book/Prob0001.json")
        root = parse_tree(sgf)
        assert root.get_property("GN") == "Prob0001"
        assert root.get_property("EV") == "Cho Chikun Elementary"
        assert root.get_property("PC") == "1a. Tsumego Beginner"
        assert root.get_property("SO").endswith("Prob0001.json")
        assert root.get_property("FF") == "4"
        assert root.get_property("GM") == "1"

    def test_escaping_of_problem_text(self):
        problem = {"AB": [], "AW": [], "SZ": 19, "C": "curve]ball \\ text", "SOL": [["B", "aa", "a]b\\c", ""]]}
        root = parse_tree(problem_to_sgf(problem))
        assert root.get_property("C") == "curve]ball \\ text"
        assert root.children[0].get_property("C") == "Solution 1: aa\na]b\\c"

    def test_missing_optional_fields(self):
        root = parse_tree(problem_to_sgf({}))
        assert root.get_list_property("AB", []) == []
        assert root.get_list_property("AW", []) == []
        assert root.get_property("C") is None
        assert root.get_property("PL") is None

    @pytest.mark.parametrize(
        "problem",
        [
            {"SZ": "big", "SOL": []},
            {"SZ": 0, "SOL": []},
            {"AB": "aa", "SOL": []},
            {"AB": ["a"], "SOL": []},
            {"AB": [3], "SOL": []},
            {"C": 5, "SOL": []},
            {"SOL": "nope"},
            {"SOL": [["B"]]},
            {"SOL": [["X", "aa"]]},
            {"SOL": [["B", 7]]},
            {"SOL": [["B", "a"]]},
            {"SOL": [["B", "aaa"]]},
        ],
    )
    def test_rejects_malformed_problems(self, problem):
        with pytest.raises(ProblemError):
            problem_to_sgf(problem)


class TestNaturalKey:
    def test_numbers_sort_numerically(self):
        assert sorted(["10.json", "2.json", "1.json"], key=natural_key) == ["1.json", "2.json", "10.json"]

    def test_number_prefixes(self):
        names = ["2b. Lee Changho Tesuji", "1a. Tsumego Beginner", "1c. Tsumego Advanced"]
        assert sorted(names, key=natural_key) == ["1a. Tsumego Beginner", "1c. Tsumego Advanced", "2b. Lee Changho Tesuji"]


class TestFindProblemFiles:
    @pytest.fixture
    def problems_root(self, tmp_path):
        for rel in [
            "1a. Cat/Book A/Prob2.json",
            "1a. Cat/Book A/Prob10.json",
            "1a. Cat/Book B/Prob1.json",
            "1b. Cat/Book C/Prob1.json",
        ]:
            path = tmp_path / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("{}", encoding="utf-8")
        (tmp_path / "1a. Cat" / "notes.txt").write_text("ignored", encoding="utf-8")
        return tmp_path

    def test_finds_and_orders_all_problems(self, problems_root):
        refs = find_problem_files(problems_root)
        assert [(ref.category, ref.book, ref.stem) for ref in refs] == [
            ("1a. Cat", "Book A", "Prob2"),
            ("1a. Cat", "Book A", "Prob10"),
            ("1a. Cat", "Book B", "Prob1"),
            ("1b. Cat", "Book C", "Prob1"),
        ]

    def test_source_path_is_portable(self, problems_root):
        ref = find_problem_files(problems_root)[0]
        assert ref.source == "1a. Cat/Book A/Prob2.json"
        assert (problems_root / ref.path).read_text(encoding="utf-8") == "{}"

    def test_refs_are_problem_refs(self, problems_root):
        assert all(isinstance(ref, ProblemRef) for ref in find_problem_files(problems_root))
