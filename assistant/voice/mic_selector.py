# assistant/voice/mic_selector.py
import sounddevice as sd

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
    "airpods"
]

def get_mme_host_api_index():
    """Finds the index for the 'MME' host API (most compatible on Windows)."""
    try:
        host_apis = sd.query_hostapis()
        for i, api in enumerate(host_apis):
            if "MME" in api["name"]:
                return i
    except:
        pass
    return None

def list_input_devices():
    devices = sd.query_devices()
    mme_index = get_mme_host_api_index()
    inputs = []

    for idx, dev in enumerate(devices):
        # 1. Must be an input device (microphone)
        if dev["max_input_channels"] <= 0:
            continue

        # 2. CRITICAL FIX: Filter out WDM-KS drivers (which cause Error -9999)
        # Only allow devices using the safe "MME" driver if available.
        if mme_index is not None and dev["hostapi"] != mme_index:
            continue

        inputs.append({
            "index": idx,
            "name": dev["name"],
            "is_default": dev.get("default_samplerate") is not None
        })

    return inputs

def is_headset(name: str) -> bool:
    lname = name.lower()
    return any(k in lname for k in HEADSET_KEYWORDS)

def auto_select_best_mic(last_used_name=None):
    # This now returns only safe MME devices
    devices = list_input_devices()

    if not devices:
        # Fallback: if MME filter removed everything (rare), try raw list
        print("⚠️ Warning: No MME devices found. Trying all devices...")
        raw_devices = sd.query_devices()
        devices = [{
            "index": i, "name": d["name"]
        } for i, d in enumerate(raw_devices) if d["max_input_channels"] > 0]

    # 1️⃣ Prefer active headset microphones
    headset_mics = [d for d in devices if is_headset(d["name"])]
    if headset_mics:
        print(f"🎤 Selected Headset (MME): {headset_mics[0]['name']}")
        return headset_mics[0]

    # 2️⃣ Prefer previously used mic if still available
    if last_used_name:
        for d in devices:
            if d["name"] == last_used_name:
                print(f"🎤 Selected Previous Mic (MME): {d['name']}")
                return d

    # 3️⃣ Fall back to first available input
    if devices:
        print(f"🎤 Selected Default Mic (MME): {devices[0]['name']}")
        return devices[0]
    
    return None