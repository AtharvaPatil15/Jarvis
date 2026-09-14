from assistant.brain.llm import ToolCall
from assistant.brain.session import Session


def test_system_prompt_is_rebuilt_on_every_call() -> None:
    counter = {"n": 0}

    def prompt() -> str:
        counter["n"] += 1
        return f"SYS {counter['n']}"

    session = Session(prompt)
    assert session.messages()[0] == {"role": "system", "content": "SYS 1"}
    assert session.messages()[0] == {"role": "system", "content": "SYS 2"}


def test_turns_and_tool_messages_use_ollama_native_shapes() -> None:
    session = Session(lambda: "SYS")
    call = ToolCall(id="c1", name="calculate", arguments={"expression": "2+2"})
    session.add_user("what is 2+2")
    session.add_assistant("", [call])
    session.add_tool_result(call, "2+2 = 4")
    session.add_assistant("Four.")
    assert session.messages()[1:] == [
        {"role": "user", "content": "what is 2+2"},
        {"role": "assistant", "content": "", "tool_calls": [{"function": {"name": "calculate", "arguments": {"expression": "2+2"}}}]},
        {"role": "tool", "tool_name": "calculate", "content": "2+2 = 4"},
        {"role": "assistant", "content": "Four."},
    ]


def test_trimming_drops_oldest_whole_turns_and_never_orphans_tool_results() -> None:
    session = Session(lambda: "SYS", max_chars=1200)
    for i in range(10):
        call = ToolCall(id=f"c{i}", name="calculate", arguments={"expression": f"{i}+1"})
        session.add_user(f"question {i} " + "x" * 150)
        session.add_assistant("", [call])
        session.add_tool_result(call, "y" * 100)
        session.add_assistant(f"answer {i}")
    messages = session.messages()
    body = messages[1:]
    assert body[0]["role"] == "user"
    assert "question 9" in body[-4]["content"]
    assert not any("question 0" in m.get("content", "") for m in body)
    for index, message in enumerate(body):
        if message["role"] == "tool":
            previous = body[index - 1]
            assert previous["role"] in ("assistant", "tool")
    assert sum(len(m.get("content") or "") for m in messages) <= 1200 + 400


def test_latest_turn_is_kept_even_when_larger_than_budget() -> None:
    session = Session(lambda: "SYS", max_chars=50)
    session.add_user("z" * 500)
    assert session.messages()[-1] == {"role": "user", "content": "z" * 500}


def test_clear_removes_history() -> None:
    session = Session(lambda: "SYS")
    session.add_user("hello")
    session.clear()
    assert session.messages() == [{"role": "system", "content": "SYS"}]