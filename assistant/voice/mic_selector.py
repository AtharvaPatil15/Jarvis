"""Selects the best available Windows input device for the voice pipeline."""
from __future__ import annotations

import logging

import sounddevice as sd

log = logging.getLogger("jarvis.voice.mic_selector")

HEADSET_KEYWORDS = [
    "headset",
    "headphone",
    "bluetooth",
    "wireless",
    "usb",
    "jbl",
    "sony",
    "boat",
    "bose",
    "airpods",
]


def get_mme_host_api_index() -> int | None:
    """Finds the index for the 'MME' host API (most compatible on Windows)."""
    try:
        host_apis = sd.query_hostapis()
    except Exception:
        return None
    for i, api in enumerate(host_apis):
        if "MME" in api["name"]:
            return i
    return None


def list_input_devices() -> list[dict[str, object]]:
    devices = sd.query_devices()
    mme_index = get_mme_host_api_index()
    inputs: list[dict[str, object]] = []

    for idx, dev in enumerate(devices):
        # 1. Must be an input device (microphone).
        if dev["max_input_channels"] <= 0:
            continue

        # 2. Only allow the "MME" driver when it exists: WDM-KS devices raise error -9999 on some hardware.
        if mme_index is not None and dev["hostapi"] != mme_index:
            continue

        inputs.append({
            "index": idx,
            "name": dev["name"],
            "is_default": dev.get("default_samplerate") is not None,
        })

    return inputs


def is_headset(name: str) -> bool:
    lname = name.lower()
    return any(k in lname for k in HEADSET_KEYWORDS)


def auto_select_best_mic(last_used_name: str | None = None) -> dict[str, object] | None:
    """Picks a headset mic if one is present, else the previously used mic, else the first input device."""
    devices = list_input_devices()

    if not devices:
        # Fallback: if the MME filter removed everything (rare), try the raw list.
        log.warning("no MME input devices found, trying all input devices")
        raw_devices = sd.query_devices()
        devices = [{"index": i, "name": d["name"]} for i, d in enumerate(raw_devices) if d["max_input_channels"] > 0]

    # 1. Prefer active headset microphones.
    headset_mics = [d for d in devices if is_headset(str(d["name"]))]
    if headset_mics:
        log.info("selected headset microphone: %s", headset_mics[0]["name"])
        return headset_mics[0]

    # 2. Prefer the previously used mic if it is still available.
    if last_used_name:
        for d in devices:
            if d["name"] == last_used_name:
                log.info("selected previous microphone: %s", d["name"])
                return d

    # 3. Fall back to the first available input.
    if devices:
        log.info("selected default microphone: %s", devices[0]["name"])
        return devices[0]

    return None
