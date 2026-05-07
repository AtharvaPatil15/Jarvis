import os

import requests


URLS = {
    "three.min.js": "https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js",
    "EffectComposer.js": "https://unpkg.com/three@0.128.0/examples/js/postprocessing/EffectComposer.js",
    "RenderPass.js": "https://unpkg.com/three@0.128.0/examples/js/postprocessing/RenderPass.js",
    "ShaderPass.js": "https://unpkg.com/three@0.128.0/examples/js/postprocessing/ShaderPass.js",
    "CopyShader.js": "https://unpkg.com/three@0.128.0/examples/js/shaders/CopyShader.js",
    "LuminosityHighPassShader.js": "https://unpkg.com/three@0.128.0/examples/js/shaders/LuminosityHighPassShader.js",
    "UnrealBloomPass.js": "https://unpkg.com/three@0.128.0/examples/js/postprocessing/UnrealBloomPass.js",
}

TARGET_DIR = os.path.join("apps", "backend", "src", "jarvis_backend", "ui", "libs")


def install():
    if not os.path.exists(TARGET_DIR):
        os.makedirs(TARGET_DIR)

    print("Downloading graphics dependencies...")

    for filename, url in URLS.items():
        save_path = os.path.join(TARGET_DIR, filename)
        try:
            print(f"Fetching {filename}...")
            response = requests.get(url)
            response.raise_for_status()
            with open(save_path, "wb") as file_handle:
                file_handle.write(response.content)
        except Exception as exc:
            print(f"Failed to download {filename}: {exc}")
            return

    print("Graphics dependencies installed successfully.")


if __name__ == "__main__":
    install()
