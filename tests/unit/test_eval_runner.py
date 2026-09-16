from pathlib import Path

from scripts.run_evals import load_cases, score_case

ROOT = Path(__file__).resolve().parents[2]


def test_the_case_file_is_valid() -> None:
    cases = load_cases(ROOT / "evals" / "commands.yaml")
    assert len(cases) == 28
    assert len({c["id"] for c in cases}) == 28
    assert all(isinstance(c["say"], list) and c["say"] for c in cases)


def test_any_all_none_and_forbidden_tools() -> None:
    turn = [{"tools": ["search_files", "read_file"], "reply": "The secret word is marigold."}]
    assert score_case({"id": "a", "say": ["x"], "expect_tools": ["read_file", "open_app"]}, turn) == (True, [])
    ok, problems = score_case({"id": "b", "say": ["x"], "expect_tools": ["read_file", "open_app"], "expect_all_tools": True}, turn)
    assert not ok and problems == ["missing tools: open_app"]
    assert score_case({"id": "c", "say": ["x"], "expect_tools": []}, turn)[1] == ["expected no tools, got: search_files, read_file"]
    assert score_case({"id": "d", "say": ["x"], "forbid_tools": ["read_file"]}, turn)[1] == ["forbidden tools used: read_file"]


def test_reply_checks_are_case_insensitive_and_use_the_last_turn() -> None:
    turns = [{"tools": [], "reply": "Rohan"}, {"tools": [], "reply": "I don't know."}]
    ok, problems = score_case({"id": "e", "say": ["x", "y"], "expect_reply": ["rohan"]}, turns)
    assert not ok and problems == ["reply is missing: rohan"]
    assert score_case({"id": "f", "say": ["x"], "expect_reply": ["MARIGOLD"]},
                      [{"tools": [], "reply": "the word is marigold"}]) == (True, [])
    assert score_case({"id": "g", "say": ["x"], "expect_reply_absent": ["marigold"]},
                      [{"tools": [], "reply": "Marigold"}])[1] == ["reply must not contain: marigold"]