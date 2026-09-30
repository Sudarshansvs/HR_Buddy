import sys
import subprocess
import time
import signal
from pathlib import Path

# Add the project root to the path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))


def wait_for_service(url, timeout=30):
    """Wait for a service to be ready."""
    import requests
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            response = requests.get(url, timeout=3)
            if response.status_code == 200:
                return True
        except (requests.ConnectionError, requests.Timeout):
            pass
        time.sleep(1)
    
    return False


def start_backend():
    """Start the FastAPI backend server."""
    print("\n" + "="*60)
    print("🚀 Starting HR Buddy Backend (FastAPI)...")
    print("   URL: http://localhost:8000")
    print("   Docs: http://localhost:8000/docs")
    print("="*60 + "\n")
    
    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "hr_buddy.app.main:app",
        "--host",
        "0.0.0.0",
        "--port",
        "8000",
        "--reload",
    ]
    
    return subprocess.Popen(cmd, cwd=str(PROJECT_ROOT))


def start_frontend():
    """Start the Streamlit frontend."""
    print("\n" + "="*60)
    print("🎨 Starting HR Buddy Frontend (Streamlit)...")
    print("   URL: http://localhost:8501")
    print("="*60 + "\n")
    
    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        "hr_buddy/frontend/streamlit_app.py",
        "--server.port",
        "8501",
        "--server.address",
        "localhost",
    ]
    
    return subprocess.Popen(cmd, cwd=str(PROJECT_ROOT))


def main():
    """Start both backend and frontend services."""
    backend_process = None
    frontend_process = None
    
    try:
        # Start backend
        backend_process = start_backend()
        
        # Wait for backend to be ready
        print("Waiting for backend to be ready...")
        if not wait_for_service("http://localhost:8000/docs", timeout=30):
            print("⚠️  Backend did not become ready in time.")
            print("   You can access it at http://localhost:8000/docs once it's ready.")
        else:
            print("✅ Backend is ready!\n")
        
        # Give backend a moment to stabilize before starting frontend
        time.sleep(2)
        
        # Start frontend
        frontend_process = start_frontend()
        
        print("\n" + "="*60)
        print("✅ HR Buddy is running!")
        print("="*60)
        print("📱 Frontend:  http://localhost:8501")
        print("🔧 Backend:   http://localhost:8000")
        print("📖 API Docs:  http://localhost:8000/docs")
        print("="*60)
        print("\nPress Ctrl+C to stop both services...\n")
        
        # Wait for both processes
        while backend_process.poll() is None and frontend_process.poll() is None:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\n" + "="*60)
        print("🛑 Shutting down HR Buddy...")
        print("="*60)
        
        # Terminate both processes
        if frontend_process and frontend_process.poll() is None:
            print("Stopping frontend...")
            frontend_process.terminate()
        
        if backend_process and backend_process.poll() is None:
            print("Stopping backend...")
            backend_process.terminate()
        
        # Wait for graceful shutdown
        try:
            if frontend_process:
                frontend_process.wait(timeout=5)
            if backend_process:
                backend_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            print("Force killing services...")
            if frontend_process:
                frontend_process.kill()
            if backend_process:
                backend_process.kill()
        
        print("✅ Shutdown complete!\n")
        

if __name__ == "__main__":
    main()
    