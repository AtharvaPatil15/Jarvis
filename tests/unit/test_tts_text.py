import pytest

from assistant.voice.tts import SentenceBuffer, Synthesizer, split_sentences


@pytest.mark.parametrize(("text", "expected"), [
    ("Hello there. How are you? Fine!", ["Hello there.", "How are you?", "Fine!"]),
    ("It costs 3.5 dollars. OK.", ["It costs 3.5 dollars.", "OK."]),
    ("Dr. Smith is here. Mr. Jones too.", ["Dr. Smith is here.", "Mr. Jones too."]),
    ("Use a tool, e.g. the calculator. Then answer.", ["Use a tool, e.g. the calculator.", "Then answer."]),
    ("Line one\nLine two", ["Line one", "Line two"]),
    ("no punctuation at all", ["no punctuation at all"]),
    ("   ", []),
])
def test_split_sentences(text: str, expected: list[str]) -> None:
    assert split_sentences(text) == expected


def test_sentence_buffer_releases_only_complete_sentences() -> None:
    buffer = SentenceBuffer()
    assert buffer.push("Hello the") == []
    assert buffer.push("re. How ") == ["Hello there."]
    assert buffer.push("are you?") == []
    assert buffer.flush() == ["How are you?"]
    assert buffer.flush() == []


def test_sentence_buffer_does_not_split_decimals_across_chunks() -> None:
    buffer = SentenceBuffer()
    assert buffer.push("It is 3.") == []
    assert buffer.push("5 degrees. Nice") == ["It is 3.5 degrees."]
    assert buffer.flush() == ["Nice"]


def test_synthesizer_reports_missing_model_files(tmp_path) -> None:
    with pytest.raises(FileNotFoundError, match="download_models.py"):
        Synthesizer(tmp_path)
