import subprocess
import time
import sys
import webbrowser

def main():
    print("=====================================================")
    print("   Starting BVR Combat Simulation Suite")
    print("=====================================================\n")
    
    print("[1/2] 🚀 Launching Streamlit Data Dashboard in background...")
    # Start streamlit in a detached process
    dashboard_proc = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "dashboard/app.py"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    
    # Wait a moment for server to bind
    time.sleep(3)
    
    # Auto-open the browser to the dashboard
    print("      🌐 Opening browser to http://localhost:8501")
    webbrowser.open("http://localhost:8501")
    
    print("\n[2/2] 🎮 Launching Pygame Tactical Visualizer Menu...")
    # Start Pygame in the foreground (blocks until user quits)
    try:
        subprocess.run([sys.executable, "main.py", "--pygame"])
    except KeyboardInterrupt:
        pass
        
    print("\n🛑 Shutting down Streamlit background server...")
    dashboard_proc.terminate()
    print("✅ Complete.")

if __name__ == "__main__":
    main()
