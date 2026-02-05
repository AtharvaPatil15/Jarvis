import os
import requests

# Libraries needed for the "Age of Ultron" glow effects
URLS = {
    "three.min.js": "https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js",
    "EffectComposer.js": "https://unpkg.com/three@0.128.0/examples/js/postprocessing/EffectComposer.js",
    "RenderPass.js": "https://unpkg.com/three@0.128.0/examples/js/postprocessing/RenderPass.js",
    "ShaderPass.js": "https://unpkg.com/three@0.128.0/examples/js/postprocessing/ShaderPass.js",
    "CopyShader.js": "https://unpkg.com/three@0.128.0/examples/js/shaders/CopyShader.js",
    "LuminosityHighPassShader.js": "https://unpkg.com/three@0.128.0/examples/js/shaders/LuminosityHighPassShader.js",
    "UnrealBloomPass.js": "https://unpkg.com/three@0.128.0/examples/js/postprocessing/UnrealBloomPass.js"
}

# Save location: assistant/ui/libs
TARGET_DIR = os.path.join("assistant", "ui", "libs")

def install():
    if not os.path.exists(TARGET_DIR):
        os.makedirs(TARGET_DIR)
        print(f"📂 Created directory: {TARGET_DIR}")

    print("⬇️  Downloading graphics engines (Three.js)...")
    
    for filename, url in URLS.items():
        save_path = os.path.join(TARGET_DIR, filename)
        try:
            print(f"   Fetching {filename}...")
            response = requests.get(url)
            response.raise_for_status()
            with open(save_path, "wb") as f:
                f.write(response.content)
        except Exception as e:
            print(f"❌ Failed to download {filename}: {e}")
            return

    print("\n✅ All graphics engines installed successfully!")
    print("   You can now run the UI offline.")

if __name__ == "__main__":
    install()
