import json

import pytest

from json_to_sgf import ExportStats, export_problems, main


@pytest.fixture
def problems_root(tmp_path):
    problems = {
        "1a. Cat/Book A/Alpha.json": {
            "AB": ["eb", "fb"], "AW": ["da"], "SZ": "19", "C": "Black to play", "SOL": [["B", "ba", "Correct.", ""]],
        },
        "1a. Cat/Book A/Beta.json": {
            "AB": ["ns"], "AW": ["nr"], "SZ": 19, "C": "White to play", "SOL": [["W", "", "", "pass wins"]],
        },
        "1a. Cat/Book B/Gamma.json": {
            "AB": ["aa"], "AW": [], "SZ": 19, "C": "", "SOL": [["B", "ab"], ["B", "ba"]],
        },
        "1b. Cat/Book C/Delta.json": {
            "AB": [], "AW": [], "SZ": 13, "C": "Small board", "SOL": [["B", "dd", "", ""]],
        },
    }
    for rel, problem in problems.items():
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(problem), encoding="utf-8")
    return tmp_path


def read(out, rel):
    return (out / rel).read_text(encoding="utf-8")


class TestExportProblems:
    def test_problems_mode_mirrors_source_layout(self, problems_root, tmp_path):
        out = tmp_path / "sgf"
        stats = export_problems(problems_root, out, mode="problems")
        assert stats.converted == 4
        assert not stats.rejected
        assert not stats.book_errors
        assert sorted(p.relative_to(out).as_posix() for p in stats.written) == [
            "1a. Cat/Book A/Alpha.sgf",
            "1a. Cat/Book A/Beta.sgf",
            "1a. Cat/Book B/Gamma.sgf",
            "1b. Cat/Book C/Delta.sgf",
        ]
        sgf = read(out, "1a. Cat/Book A/Alpha.sgf")
        assert "GN[Alpha]" in sgf
        assert "EV[Book A]" in sgf
        assert "PC[1a. Cat]" in sgf
        assert "SO[1a. Cat/Book A/Alpha.json]" in sgf

    def test_books_mode_writes_one_game_per_book(self, problems_root, tmp_path):
        out = tmp_path / "sgf"
        stats = export_problems(problems_root, out, mode="books")
        assert stats.converted == 4
        assert sorted(p.relative_to(out).as_posix() for p in stats.written) == [
            "1a. Cat/Book A.sgf",
            "1a. Cat/Book B.sgf",
            "1b. Cat/Book C.sgf",
        ]
        book = read(out, "1a. Cat/Book A.sgf")
        assert book.count("(;") >= 1
        root = pytest.importorskip("pysgf").GoGame(book).root
        assert root.get_property("EV") == "Book A"
        assert root.get_property("PC") == "1a. Cat"
        assert len(root.children) == 2
        first, second = root.children
        assert first.get_property("C").startswith("Alpha\n\nBlack to play")
        assert first.get_list_property("AB") == ["eb", "fb"]
        assert second.get_property("C").startswith("Beta\n\nWhite to play")
        assert second.children[0].get_property("W") == ""

    def test_books_mode_rejects_mixed_board_sizes(self, problems_root, tmp_path):
        (problems_root / "1a. Cat/Book A/Oversize.json").write_text(
            json.dumps({"AB": [], "AW": [], "SZ": 25, "SOL": []}), encoding="utf-8"
        )
        out = tmp_path / "sgf"
        stats = export_problems(problems_root, out, mode="books")
        assert stats.converted == 5
        assert stats.book_errors == ["1a. Cat/Book A: book mixes board sizes [19, 25]; export it per board size"]
        assert not (out / "1a. Cat/Book A.sgf").exists()
        assert (out / "1a. Cat/Book B.sgf").exists()

    def test_both_mode_writes_both_layouts(self, problems_root, tmp_path):
        out = tmp_path / "sgf"
        stats = export_problems(problems_root, out, mode="both")
        assert (out / "1a. Cat/Book A/Alpha.sgf").exists()
        assert (out / "1a. Cat/Book A.sgf").exists()
        assert len(stats.written) == 7

    def test_invalid_problem_is_rejected_and_export_continues(self, problems_root, tmp_path):
        (problems_root / "1a. Cat/Book A/Broken.json").write_text('{"AB": "not-a-list", "SZ": 19, "SOL": []}', encoding="utf-8")
        (problems_root / "1a. Cat/Book A/Unparseable.json").write_text("{not json", encoding="utf-8")
        stats = export_problems(problems_root, tmp_path / "sgf", mode="problems")
        assert stats.converted == 4
        assert sorted(ref.stem for ref, _ in stats.rejected) == ["Broken", "Unparseable"]
        assert all("AB must be a list" in reason or "cannot read problem JSON" in reason for _, reason in stats.rejected)

    def test_unknown_mode_raises(self, problems_root, tmp_path):
        with pytest.raises(ValueError):
            export_problems(problems_root, tmp_path, mode="nope")


class TestMain:
    def test_main_reports_and_exit_codes(self, problems_root, tmp_path, capsys):
        (problems_root / "1a. Cat/Book A/Broken.json").write_text('{"SZ": 19, "SOL": [["X", "aa"]]}', encoding="utf-8")
        out = tmp_path / "sgf"
        exit_code = main(["--problems-root", str(problems_root), "--out", str(out), "--mode", "both"])
        captured = capsys.readouterr()
        assert exit_code == 1
        assert "rejected 1a. Cat/Book A/Broken.json" in captured.err
        assert "Converted 4 problems (1 rejected" in captured.out

    def test_main_clean_run_exits_zero(self, problems_root, tmp_path, capsys):
        exit_code = main(["--problems-root", str(problems_root), "--out", str(tmp_path / "sgf")])
        assert exit_code == 0
        assert "Converted 4 problems (0 rejected" in capsys.readouterr().out


def test_export_stats_defaults():
    stats = ExportStats()
    assert stats.converted == 0
    assert stats.rejected == []
    assert stats.book_errors == []
    assert stats.written == []
