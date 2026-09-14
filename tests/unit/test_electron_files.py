import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_preload_script_referenced_by_electron_main_exists() -> None:
    main_js = (ROOT / "electron" / "main.js").read_text(encoding="utf-8")
    match = re.search(r"path\.join\(__dirname,\s*[\"']([^\"']+)[\"']\)", main_js)
    assert match, "electron/main.js must reference a preload script"
    assert (ROOT / "electron" / match.group(1)).is_file()