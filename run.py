import subprocess
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent


def wait_for_backend(url: str, timeout: int = 30):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            response = requests.get(url, timeout=2)
            if response.status_code < 500:
                return True
        except requests.RequestException:
            pass
        time.sleep(1)
    return False


def start_backend():
    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "llm_test_2:app",
        "--host",
        "127.0.0.1",
        "--port",
        "8080",
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
    if not wait_for_backend("http://127.0.0.1:8080/docs"):
        print("Backend did not become ready in time. Check uvicorn logs.")
    frontend = start_frontend()

    try:
        backend.wait()
    except KeyboardInterrupt:
        print("\nStopping HR Buddy...")
        backend.terminate()
        frontend.terminate()
        backend.wait()
        frontend.wait()
