"""Bounded local entry points for the skill. Stdout is sanitized JSON."""
from pathlib import Path
import json
import os
import subprocess
import sys
import time

APP = Path(__file__).resolve().parents[1] / "app"
sys.path.insert(0, str(APP))
import widget

def run(action):
    if action == "status":
        try:
            windows = widget.fetch_limits()
        except widget.UsageError as error:
            return {"ok": False, "error": str(error)}, 1
        except Exception:
            return {"ok": False, "error": "Unable to read limits. Check the installed Codex CLI and sign-in."}, 1
        return {"ok": True, "observed_at": int(time.time()), "windows": [
            {"remaining": w.remaining, "minutes": w.minutes, "reset": w.reset} for w in windows]}, 0
    if action == "open":
        if os.name != "nt":
            return {"ok": False, "error": "The desktop card requires Windows."}, 1
        pythonw = Path(sys.executable).with_name("pythonw.exe")
        if not pythonw.is_file():
            return {"ok": False, "error": "pythonw.exe with Tk is required. Install standard Python 3.11+."}, 1
        try:
            process = subprocess.Popen([str(pythonw), str(APP / "widget.py")], cwd=str(APP),
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW)
            try:
                result = process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                return {"ok": True, "state": "launch_requested", "version": widget.VERSION}, 0
            if result == 0:
                return {"ok": True, "state": "already_running_or_closed", "version": widget.VERSION}, 0
        except OSError:
            pass
        return {"ok": False, "error": "The card could not start. Try app/Launch Widget.vbs."}, 1
    return {"ok": False, "error": "Choose status or open."}, 2

if __name__ == "__main__":
    result, code = run(sys.argv[1] if len(sys.argv) == 2 else "")
    print(json.dumps(result))
    sys.exit(code)
