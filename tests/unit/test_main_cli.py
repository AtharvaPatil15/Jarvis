import asyncio

import main


def test_repl_answers_each_line_until_exit(monkeypatch) -> None:
    monkeypatch.setenv("JARVIS_LLM_BACKEND", "fake")
    lines = iter(["hello", "   ", "exit"])
    output: list[str] = []
    asyncio.run(main.repl(read=lambda prompt: next(lines), write=output.append))
    assert output == ["JARVIS text mode. Type 'exit' to quit.", "jarvis> You said: hello"]