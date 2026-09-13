import json
import os

import pytest

from scripts.probe_llm import probe

pytestmark = pytest.mark.live

URL = os.environ.get("JARVIS_OLLAMA_URL", "http://127.0.0.1:11434")
MODEL = os.environ.get("JARVIS_CHAT_MODEL", "qwen3:8b")
EMBED = os.environ.get("JARVIS_EMBED_MODEL", "nomic-embed-text")


def test_probe_reports_every_capability_ok() -> None:
    report = probe(URL, MODEL, EMBED)
    failed = {name: check for name, check in report["checks"].items() if not check["ok"]}
    assert not failed, json.dumps(failed, indent=2)
    assert report["embedding_dim"] > 0