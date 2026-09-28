import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def start_backend():
    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "llm_test_2:app",
        "--host",
        "127.0.0.1",
        "--port",
        "8000",
    ]
    print("Starting HR Buddy backend...")
    return subprocess.Popen(cmd, cwd=str(ROOT))


def start_frontend():
    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        "app.py",
        "--server.headless",
        "true",
    ]
    print("Starting HR Buddy frontend...")
    return subprocess.Popen(cmd, cwd=str(ROOT))


if __name__ == "__main__":
    backend = start_backend()
    time.sleep(2)
    frontend = start_frontend()

    try:
        backend.wait()
    except KeyboardInterrupt:
        print("\nStopping HR Buddy...")
        backend.terminate()
        frontend.terminate()
        backend.wait()
        frontend.wait()
