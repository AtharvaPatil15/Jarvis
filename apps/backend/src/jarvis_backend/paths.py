from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
DATA_DIR = REPO_ROOT / "data"
STATE_DIR = DATA_DIR / "state"
RUNTIME_DIR = DATA_DIR / "runtime"
AUDIO_DIR = RUNTIME_DIR / "audio"
CONFIG_DIR = REPO_ROOT / "config"


def ensure_runtime_dirs() -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
