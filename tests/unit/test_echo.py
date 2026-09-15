from assistant.voice.echo import EchoGuard


class Clock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now


def test_hearing_our_own_sentence_is_echo() -> None:
    guard = EchoGuard()
    guard.note_spoken("I have opened YouTube for you.")
    assert guard.is_echo("i have opened youtube for you")
    assert guard.is_echo("have opened YouTube for")


def test_echo_can_span_consecutive_sentences() -> None:
    guard = EchoGuard()
    guard.note_spoken("Sure.")
    guard.note_spoken("It is five o'clock.")
    assert guard.is_echo("sure it is five o'clock")


def test_real_commands_are_not_echo() -> None:
    guard = EchoGuard()
    guard.note_spoken("Done.")
    assert not guard.is_echo("what's the weather in Mumbai")
    assert not guard.is_echo("I'm done with that, now open my notes")
    assert not guard.is_echo("stop")


def test_old_speech_expires_after_the_window() -> None:
    clock = Clock()
    guard = EchoGuard(window_s=8.0, clock=clock)
    guard.note_spoken("I have opened YouTube for you.")
    clock.now += 9.0
    assert not guard.is_echo("i have opened youtube for you")
