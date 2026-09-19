"""
CoCompute Universal Worker Launcher
Cross-platform auto-runner for Windows, Linux, and macOS.

Usage:
    python start_worker.py          # Auto-launches Desktop GUI (or Headless fallback)
    python start_worker.py --gui    # Launch Desktop GUI
    python start_worker.py --cli    # Launch Headless Terminal Mode
"""

import sys
import os
import subprocess

# Ensure paths are configured regardless of where the script is invoked from
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)

for path in (CURRENT_DIR, PARENT_DIR):
    if path not in sys.path:
        sys.path.insert(0, path)


def auto_install_requirements():
    """Verify core dependencies exist. If not, auto-install them smoothly."""
    core_packages = ["psutil", "websockets", "httpx"]
    missing = []
    for pkg in core_packages:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)

    if missing:
        print(f"[*] CoCompute: Missing required packages {missing}. Auto-installing...")
        req_file = os.path.join(CURRENT_DIR, "requirements.txt")
        try:
            if os.path.exists(req_file):
                subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", req_file])
            else:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "psutil>=6.0.0", "websockets>=12.0", "httpx>=0.27.0", "PySide6>=6.7.0"])
            print("[✓] Dependencies installed successfully.\n")
        except Exception as e:
            print(f"[!] Warning: Could not auto-install: {e}")
            print("Please run: pip install -r requirements.txt")


if __name__ == "__main__":
    auto_install_requirements()

    # Determine execution entrypoint
    try:
        from worker.app.main import main
    except ImportError:
        try:
            from app.main import main
        except ImportError as e:
            print(f"[!] Error loading worker module: {e}")
            sys.exit(1)

    # If no flags provided, default to --gui if PySide6 is available, else headless
    if len(sys.argv) == 1:
        try:
            import PySide6
            sys.argv.append("--gui")
        except ImportError:
            pass  # Run in headless mode

    if "--cli" in sys.argv:
        sys.argv.remove("--cli")
        if "--gui" in sys.argv:
            sys.argv.remove("--gui")

    main()
