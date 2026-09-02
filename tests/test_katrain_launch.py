import pytest

controller = pytest.importorskip("controller")  # pulls in kivy


def test_problem_sgf_path_mirrors_problems_tree():
    path = controller.problem_sgf_path("problems/1a. Cat/Book B/Prob2.json")
    assert path.is_absolute()
    assert path.parts[-4:] == ("tsumego_sgf", "1a. Cat", "Book B", "Prob2.sgf")


def test_launch_failure_returns_message(monkeypatch):
    def boom(*args, **kwargs):
        raise FileNotFoundError("KaTrain not found")

    monkeypatch.setattr(controller.subprocess, "run", boom)
    message = controller.launch_in_katrain("/tmp/whatever.sgf")
    assert "Could not launch KaTrain" in message
    assert "KaTrain not found" in message


def test_launch_success_returns_none(monkeypatch):
    calls = []
    monkeypatch.setattr(controller.subprocess, "run", lambda cmd, **k: calls.append(cmd))
    if controller.platform == "win":
        pytest.skip("windows uses os.startfile")
    assert controller.launch_in_katrain("/tmp/whatever.sgf") is None
    assert calls and "KaTrain" in calls[0]
