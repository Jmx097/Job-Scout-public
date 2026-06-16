"""
Job Scout — One-click launcher
Starts the Flask server in a background thread, opens the browser,
then keeps running until the window is closed.
"""

import os
import sys
import time
import socket
import threading
import webbrowser

# ── Path setup for PyInstaller bundles ─────────────────────────────────────
if getattr(sys, "frozen", False):
    # Running as a compiled exe — resources live in sys._MEIPASS
    BUNDLE_DIR = sys._MEIPASS
    # CWD should be next to the exe so uploads/ is writable
    os.chdir(os.path.dirname(sys.executable))
else:
    BUNDLE_DIR = os.path.dirname(os.path.abspath(__file__))

# Make sure app.py can find its own modules
if BUNDLE_DIR not in sys.path:
    sys.path.insert(0, BUNDLE_DIR)

PORT = int(os.environ.get("PORT", 5000))


def _port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("localhost", port)) != 0


def _wait_for_server(port: int, timeout: float = 15.0) -> bool:
    start = time.time()
    while time.time() - start < timeout:
        if not _port_free(port):
            return True
        time.sleep(0.2)
    return False


def _run_flask():
    # Import here so the frozen bundle can resolve it
    import app as scout_app
    scout_app.app.run(
        host="0.0.0.0",
        port=PORT,
        debug=False,
        use_reloader=False,
        threaded=True,
    )


def main():
    # If something is already on the port, just open the browser
    if not _port_free(PORT):
        webbrowser.open(f"http://localhost:{PORT}")
        return

    print(f"  🔍  Job Scout")
    print(f"  ─────────────────────────────")
    print(f"  Starting server on port {PORT}…")

    server = threading.Thread(target=_run_flask, daemon=True)
    server.start()

    if _wait_for_server(PORT):
        print(f"  ✓  Running at http://localhost:{PORT}")
        print(f"  Close this window to stop Job Scout.\n")
        webbrowser.open(f"http://localhost:{PORT}")
    else:
        print(f"  ✗  Server failed to start. Check that port {PORT} is free.")
        sys.exit(1)

    # Block until Ctrl-C or window close
    try:
        server.join()
    except KeyboardInterrupt:
        print("\n  Stopping Job Scout…")


if __name__ == "__main__":
    main()
