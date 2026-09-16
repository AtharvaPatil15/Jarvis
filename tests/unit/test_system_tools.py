from pathlib import Path

from assistant.config import Settings
from assistant.tools.builtin import build_default_registry
from assistant.tools.builtin.system import MediaControlTool, OpenAppTool, OpenUrlTool


def shortcuts(tmp_path: Path) -> Path:
    programs = tmp_path / "Programs"
    (programs / "Google").mkdir(parents=True, exist_ok=True)
    for relative in ["Google/Google Chrome.lnk", "Visual Studio Code.lnk", "Spotify.lnk", "Uninstall Spotify.lnk"]:
        (programs / relative).write_bytes(b"")
    return programs


def test_open_app_launches_the_best_matching_shortcut(tmp_path) -> None:
    launched: list[str] = []
    tool = OpenAppTool([shortcuts(tmp_path)], launcher=launched.append)
    assert tool.run(tool.parse_args({"name": "chrome"})) == "Opened Google Chrome."
    assert launched == [str(tmp_path / "Programs" / "Google" / "Google Chrome.lnk")]


def test_synonyms_aliases_and_uninstallers(tmp_path) -> None:
    tool = OpenAppTool([shortcuts(tmp_path)], launcher=lambda target: None)
    assert tool.resolve("vs code").endswith("Visual Studio Code.lnk")
    assert tool.resolve("Notepad") == "notepad.exe"
    assert tool.resolve("uninstall spotify").endswith(str(Path("Programs") / "Spotify.lnk"))


def test_unknown_app_and_launch_failure(tmp_path) -> None:
    launched: list[str] = []
    tool = OpenAppTool([shortcuts(tmp_path)], launcher=launched.append)
    assert tool.run(tool.parse_args({"name": "flux capacitor"})) == "ERROR: no installed app matches 'flux capacitor'"
    assert launched == []

    def denied(target: str) -> None:
        raise OSError("access denied")

    failing = OpenAppTool([shortcuts(tmp_path)], launcher=denied)
    assert failing.run(failing.parse_args({"name": "notepad"})) == "ERROR: could not open notepad: access denied"


def test_open_url_only_allows_web_addresses() -> None:
    opened: list[str] = []
    tool = OpenUrlTool(opener=lambda url: opened.append(url) or True)
    assert tool.run(tool.parse_args({"url": "https://www.youtube.com"})) == "Opened https://www.youtube.com."
    for bad in ["javascript:alert(1)", "file:///C:/Windows/win.ini", "youtube.com"]:
        assert tool.run(tool.parse_args({"url": bad})) == "ERROR: only http and https URLs can be opened"
    assert opened == ["https://www.youtube.com"]


def test_media_control_presses_the_right_keys() -> None:
    pressed: list[int] = []
    tool = MediaControlTool(press=pressed.append)
    assert tool.run(tool.parse_args({"action": "volume_up", "steps": 3})) == "Done: volume up x3."
    assert tool.run(tool.parse_args({"action": "play_pause", "steps": 5})) == "Done: play pause."
    assert pressed == [0xAF, 0xAF, 0xAF, 0xB3]


def test_default_registry_includes_system_tools() -> None:
    assert {"open_app", "open_url", "media_control"} <= set(build_default_registry(Settings(_env_file=None)).names())
