import os
import sys
import shutil
import subprocess
from pathlib import Path

# Load .env
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip().strip('"\'')

config_file = Path(__file__).parent / "litellm_config.yaml"

def find_litellm_exe():
    exe = shutil.which("litellm")
    if exe:
        return exe
    user_appdata_exe = Path(os.environ.get("APPDATA", "")) / r"..\Roaming\Python\Python311\Scripts\litellm.exe"
    if user_appdata_exe.exists():
        return str(user_appdata_exe.resolve())
    return "litellm"

litellm_bin = find_litellm_exe()

print("==================================================================")
print("🚀 Starting Industry Standard LiteLLM Proxy Gateway...")
print(f"🔑 Key Auto-Loaded from: {env_path}")
print(f"📄 Config File: {config_file}")
print(f"🛠 Executable: {litellm_bin}")
print("🌐 Proxy URL: http://127.0.0.1:8000")
print("==================================================================\n")

cmd = [
    litellm_bin,
    "--config", str(config_file),
    "--port", "8000"
]

try:
    subprocess.run(cmd)
except KeyboardInterrupt:
    print("\n[!] LiteLLM Proxy Gateway stopped.")
