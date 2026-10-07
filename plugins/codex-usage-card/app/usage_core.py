"""A read-only Windows usage card. Python 3.11+ / Tk; no third-party packages."""
from __future__ import annotations

import argparse
import ctypes
from dataclasses import dataclass
from datetime import datetime
import json
import math
import os
from pathlib import Path
import queue
import shutil
import subprocess
import tempfile
import threading
import time
import tkinter as tk
from tkinter import messagebox

VERSION = "0.3.0"
REFRESH_SECONDS = 300
RPC_TIMEOUT = 25
BG, PANEL, TEXT, MUTED = "#252d32", "#354149", "#f4f8f8", "#b5c4c9"
TEAL, CORAL, LINE = "#70e2d4", "#ffb19d", "#4c5b63"


class UsageError(Exception):
    """Safe user-facing errors; never display arbitrary server responses."""


@dataclass(frozen=True)
class Window:
    remaining: float
    minutes: int | None
    reset: int | None

    @property
    def label(self):
        if self.minutes == 10080:
            return "Weekly limit"
        if self.minutes and self.minutes < 1440:
            return f"{self.minutes / 60:g}-hour limit"
        if self.minutes == 1440:
            return "Daily limit"
        return "Plan limit"


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def parse_window(raw):
    if not isinstance(raw, dict) or not number(raw.get("usedPercent")):
        return None
    duration = raw.get("windowDurationMins")
    duration = int(duration) if number(duration) and duration > 0 else None
    reset = raw.get("resetsAt")
    # Only supported Unix seconds, not milliseconds or arbitrary strings.
    reset = int(reset) if number(reset) and 0 < reset < 253402300800 else None
    return Window(max(0, min(100, 100 - raw["usedPercent"])), duration, reset)


def parse_limits(result):
    if not isinstance(result, dict):
        raise UsageError("Codex returned no usage data.")
    buckets = result.get("rateLimitsByLimitId")
    snapshot = buckets.get("codex") if isinstance(buckets, dict) else None
    if not isinstance(snapshot, dict):
        snapshot = result.get("rateLimits")
    # A named unrelated model bucket must not masquerade as the Codex limit.
    if not isinstance(snapshot, dict) or snapshot.get("limitId") not in (None, "codex"):
        raise UsageError("Codex plan limits are unavailable.")
    windows = [parse_window(snapshot.get(key)) for key in ("primary", "secondary")]
    windows = [w for w in windows if w is not None]
    if not windows:
        raise UsageError("No plan window is available. Try Refresh.")
    return sorted(windows, key=lambda w: w.minutes or 0, reverse=True)


def countdown(reset, now=None):
    if reset is None:
        return "Reset time unavailable"
    seconds = reset - (time.time() if now is None else now)
    if seconds <= 0:
        return "Reset time reached · awaiting update"
    minutes = math.ceil(seconds / 60)
    days, minutes = divmod(minutes, 1440)
    hours, minutes = divmod(minutes, 60)
    parts = ([f"{days}d"] if days else []) + ([f"{hours}h"] if hours else [])
    if not days or not hours:
        parts.append(f"{minutes}m")
    return "Resets in " + " ".join(parts)


def percentage(value):
    return f"{value:.0f}%" if value == int(value) else f"{value:.1f}%"


def find_codex():
    found = shutil.which("codex")
    if found and Path(found).suffix.lower() == ".exe":
        return found
    root = Path(os.environ.get("LOCALAPPDATA", "")) / "OpenAI" / "Codex" / "bin"
    candidates = list(root.glob("*/codex.exe")) if root.is_dir() else []
    if candidates:
        return str(max(candidates, key=lambda p: p.stat().st_mtime))
    raise UsageError("Codex CLI not found. Open or update the Codex app.")


def fetch_limits(executable=None, timeout=RPC_TIMEOUT, cancel=None):
    """Only initialize + account/rateLimits/read. No auth file access or model turns."""
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    process = None
    try:
        process = subprocess.Popen(
            [executable or find_codex(), "app-server", "--stdio", "-c", "analytics.enabled=false"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            encoding="utf-8", text=True, creationflags=flags,
        )
        messages = queue.Queue(maxsize=100)

        def read_lines():
            try:
                while True:
                    line = process.stdout.readline(1048577)
                    if not line:
                        break
                    if len(line) > 1048576:
                        break
                    try:
                        msg = json.loads(line)
                    except ValueError:
                        continue
                    if isinstance(msg, dict) and "id" in msg and ("result" in msg or "error" in msg):
                        messages.put_nowait(msg)
            except (OSError, ValueError, queue.Full):
                pass
            finally:
                try:
                    messages.put_nowait(None)
                except queue.Full:
                    pass

        threading.Thread(target=read_lines, daemon=True).start()
        deadline = time.monotonic() + timeout

        def send(message):
            process.stdin.write(json.dumps(message) + "\n")
            process.stdin.flush()

        def request(method, params, ident):
            send({"id": ident, "method": method, "params": params})
            while True:
                if cancel is not None and cancel.is_set():
                    raise UsageError("Refresh cancelled.")
                left = deadline - time.monotonic()
                if left <= 0:
                    raise UsageError("Refresh timed out. Try again when online.")
                try:
                    msg = messages.get(timeout=min(left, 0.2))
                except queue.Empty:
                    continue
                if msg is None:
                    raise UsageError("Codex closed the usage connection.")
                if msg.get("id") != ident:
                    continue
                if "error" in msg:
                    raise UsageError("Could not read limits. Check your Codex sign-in, then Refresh.")
                return msg.get("result")

        request("initialize", {
            "clientInfo": {"name": "kreadiv_usage_widget", "title": "Codex Usage Widget", "version": VERSION},
            "capabilities": {"explicitGatewayOauth": True},
        }, 1)
        send({"method": "initialized"})
        result = request("account/rateLimits/read", {
            "excludeResetCreditDetails": True, "supportsLunaReserve": False,
        }, 2)
        return parse_limits(result)
    except (OSError, ValueError):
        raise UsageError("Could not start Codex. Open the Codex app, then Refresh.") from None
    finally:
        if process is not None:
            if process.poll() is None:
                process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=3)
            for stream in (process.stdin, process.stdout):
                if stream:
                    stream.close()


def load_preferences(path):
    try:
        if path.stat().st_size > 4096:
            return {}
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return {}
        return {key: data[key] for key in ("x", "y", "topmost") if key in data}
    except (OSError, ValueError):
        return {}


def save_preferences(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


class Widget:
    WIDTH = 282

    def __init__(self, root, settings_path, status_path=None, auto_start=True):
        self.root, self.settings_path, self.status_path = root, settings_path, status_path
        self.results = queue.Queue()
        self.windows = []
        self.updated_at = None
        self.busy = self.failed = self.closed = False
        self.failures = 0
        self.next_refresh = time.monotonic()
        self.expired_refetched = set()
        self.cancel = threading.Event()
        self.worker = None
        self.frame_size = None
        self.rounding_applied = False
        self.drag_offset = None
        prefs = load_preferences(settings_path)
        root.title("Codex usage")
        root.configure(bg=BG)
        root.resizable(False, False)
        root.overrideredirect(True)
        if os.name == 'nt':
            root.attributes('-alpha', 0.96)
        x = prefs.get('x', root.winfo_screenwidth() - 310)
        y = prefs.get('y', root.winfo_screenheight() - 240)
        x = int(x) if number(x) else 80
        y = int(y) if number(y) else 80
        x = max(0, min(x, max(0, root.winfo_screenwidth() - self.WIDTH)))
        y = max(0, min(y, max(0, root.winfo_screenheight() - 241)))
        root.geometry(f'{self.WIDTH}x176+{x}+{y}')
        self.topmost = tk.BooleanVar(value=prefs.get('topmost') is True)
        root.attributes('-topmost', self.topmost.get())
        root.protocol('WM_DELETE_WINDOW', self.close)
        root.bind('<Control-r>', lambda event: self.refresh())
        root.bind('<Escape>', lambda event: self.close())
        root.bind('<Alt-F4>', lambda event: self.close())
        root.bind('<Button-3>', self.open_menu)
        root.bind('<Configure>', self.on_configure)

        mark = Path(__file__).resolve().parent / 'assets' / 'studio-mark.png'
        if mark.is_file():
            try:
                self.icon = tk.PhotoImage(file=str(mark))
                root.iconphoto(True, self.icon)
            except tk.TclError:
                pass
        self.body = body = tk.Frame(root, bg=BG, highlightbackground=LINE, highlightthickness=1)
        body.pack(fill='both', expand=True)
        if hasattr(self, 'icon'):
            self.header_icon = self.icon.subsample(max(1, math.ceil(self.icon.width() / 17)))
            tk.Label(body, image=self.header_icon, bg=BG, bd=0).place(x=18, y=17, width=18, height=18)
        tk.Label(body, text='Codex', font=('Segoe UI', -14, 'bold'), fg=TEXT, bg=BG, bd=0).place(x=42, y=17)
        self.state_label = tk.Label(body, text='Connecting', font=('Segoe UI', -9), fg=MUTED, bg=BG, bd=0)
        self.state_label.place(x=169, y=23, anchor='e')
        self.close_button = self.button(body, 'Close', self.close)
        self.close_button.place(x=222, y=16, width=41, height=22)

        self.rows = []
        for index in range(2):
            row = tk.Frame(body, bg=BG)
            name = tk.Label(row, text='Plan limit', font=('Segoe UI', -12), fg=TEXT, bg=BG, bd=0, anchor='w')
            name.place(x=0, y=1, width=110, height=21)
            value = tk.Label(row, text='—', font=('Segoe UI', -17, 'bold'), fg=TEXT, bg=BG, bd=0, anchor='e')
            value.place(x=112, y=0, width=132, height=25)
            bar = tk.Canvas(row, height=6, bg=BG, highlightthickness=0, bd=0)
            bar.place(x=2, y=29, width=240, height=6)
            reset = tk.Label(row, text='Reading current limits…', font=('Segoe UI', -10), fg=MUTED, bg=BG,
                             bd=0, anchor='w')
            reset.place(x=0, y=39, width=244, height=16)
            self.rows.append({'frame': row, 'name': name, 'value': value, 'bar': bar, 'reset': reset})
        self.limit_label = self.rows[0]['name']
        self.value_label = self.rows[0]['value']
        self.bar = self.rows[0]['bar']
        self.reset_label = self.rows[0]['reset']
        self.detail_label = tk.Label(body, text='', font=('Segoe UI', -10), fg=CORAL, bg=BG, bd=0,
                                     wraplength=244, anchor='nw', justify='left')
        self.refresh_button = self.button(body, 'Refresh', self.refresh)
        self.pin_button = tk.Checkbutton(body, text='Pin', variable=self.topmost, command=self.toggle_topmost,
            font=('Segoe UI', -10), bg=BG, fg=MUTED, activebackground=PANEL, activeforeground=TEXT,
            selectcolor=PANEL, indicatoron=False, bd=0, padx=0, highlightthickness=1,
            highlightbackground=BG, highlightcolor=TEAL, cursor='hand2', takefocus=True)
        self.menu_button = self.button(body, 'Menu', self.open_menu)
        self.updated_label = tk.Label(body, text='Auto refresh · 5 min', font=('Segoe UI', -9), fg=MUTED, bg=BG, bd=0, anchor='w')
        self.version_label = tk.Label(body, text=f'v{VERSION}', font=('Segoe UI', -9), fg=MUTED, bg=BG, bd=0)
        self.menu = tk.Menu(root, tearoff=0, bg=BG, fg=TEXT, activebackground=PANEL, activeforeground=TEAL)
        self.menu.add_command(label='Refresh now', command=self.refresh)
        self.menu.add_checkbutton(label='Stay on top', variable=self.topmost, command=self.toggle_topmost)
        self.menu.add_command(label='Reset details', command=self.reset_details)
        self.menu.add_command(label='About', command=self.about)
        self.menu.add_separator()
        self.menu.add_command(label='Close widget', command=self.close)
        self.layout_content()
        self.update_pin_text()
        self.bind_drag(body)
        root.after(60, self.style_window)
        self.auto_start = auto_start
        if auto_start:
            root.after(150, self.refresh)
        root.after(200, self.tick)

    @staticmethod
    def button(parent, text, command):
        return tk.Button(parent, text=text, command=command, font=('Segoe UI', -10), bg=BG, fg=MUTED,
            activebackground=PANEL, activeforeground=TEAL, disabledforeground=MUTED,
            bd=0, padx=0, pady=0, cursor='hand2', takefocus=True, highlightthickness=1,
            highlightbackground=BG, highlightcolor=TEAL)

    def bind_drag(self, node):
        if not isinstance(node, (tk.Button, tk.Checkbutton)):
            node.bind('<ButtonPress-1>', self.begin_drag)
            node.bind('<B1-Motion>', self.drag)
            node.bind('<ButtonRelease-1>', self.end_drag)
        for child in node.winfo_children():
            self.bind_drag(child)

    def begin_drag(self, event):
        self.drag_offset = (event.x_root - self.root.winfo_x(), event.y_root - self.root.winfo_y())

    def drag(self, event):
        if self.drag_offset:
            x = event.x_root - self.drag_offset[0]
            y = event.y_root - self.drag_offset[1]
            self.root.geometry(f'+{x}+{y}')

    def end_drag(self, event):
        if self.drag_offset:
            self.drag_offset = None
            try:
                self.persist()
            except OSError:
                pass

    def display_windows(self):
        # Matches the reference: short limit first, weekly underneath when both exist.
        return sorted(self.windows, key=lambda window: window.minutes or 1000000)

    def layout_content(self):
        count = max(1, min(2, len(self.windows)))
        error_height = 32 if self.failed else 0
        height = 176 + (count - 1) * 65 + error_height
        if self.root.winfo_height() != height:
            self.root.geometry(f'{self.WIDTH}x{height}')
        for index, row in enumerate(self.rows):
            if index < count:
                row['frame'].place(x=18, y=51 + index * 65, width=244, height=59)
            else:
                row['frame'].place_forget()
        if self.failed:
            self.detail_label.place(x=18, y=116 + (count - 1) * 65, width=244, height=30)
        else:
            self.detail_label.place_forget()
        self.refresh_button.place(x=18, y=height - 57, width=60, height=23)
        self.pin_button.place(x=91, y=height - 57, width=62, height=23)
        self.menu_button.place(x=220, y=height - 57, width=43, height=23)
        self.updated_label.place(x=19, y=height - 22, anchor='w')
        self.version_label.place(x=262, y=height - 22, anchor='e')

    def on_configure(self, event):
        if event.widget is self.root:
            self.style_window()

    def style_window(self):
        """Round only this app's borderless HWND, using native window composition."""
        if os.name != 'nt' or self.closed:
            return
        size = (self.root.winfo_width(), self.root.winfo_height())
        if size == self.frame_size or min(size) < 2:
            return
        try:
            from ctypes import wintypes
            get_parent = ctypes.windll.user32.GetParent
            get_parent.argtypes = [wintypes.HWND]
            get_parent.restype = wintypes.HWND
            hwnd = get_parent(self.root.winfo_id())
            create_region = ctypes.windll.gdi32.CreateRoundRectRgn
            create_region.argtypes = [ctypes.c_int] * 6
            create_region.restype = wintypes.HANDLE
            set_region = ctypes.windll.user32.SetWindowRgn
            set_region.argtypes = [wintypes.HWND, wintypes.HANDLE, wintypes.BOOL]
            region = create_region(0, 0, size[0] + 1, size[1] + 1, 28, 28)
            if region:
                self.rounding_applied = bool(set_region(hwnd, region, True))
                if not self.rounding_applied:
                    delete_region = ctypes.windll.gdi32.DeleteObject
                    delete_region.argtypes = [wintypes.HANDLE]
                    delete_region(region)
            self.frame_size = size
        except (AttributeError, OSError):
            pass

    def update_pin_text(self):
        self.pin_button.config(text='Pinned' if self.topmost.get() else 'Pin')

    def draw_bar(self):
        windows = self.display_windows()
        for index, row in enumerate(self.rows):
            bar = row['bar']
            bar.delete('all')
            width = 234
            bar.create_line(3, 3, 3 + width, 3, fill=LINE, width=4, capstyle='round')
            if index < len(windows):
                fill_width = width * windows[index].remaining / 100
                color = CORAL if windows[index].remaining <= 15 else TEAL
                if fill_width > 0:
                    bar.create_line(3, 3, 3 + fill_width, 3, fill=color, width=4, capstyle='round')

    def refresh(self):
        if self.busy or self.closed:
            return
        self.busy = True
        self.state_label.config(text='Refreshing', fg=MUTED)
        self.refresh_button.config(state='disabled')
        def work():
            try:
                self.results.put((fetch_limits(cancel=self.cancel), None))
            except UsageError as error:
                self.results.put((None, str(error)))
            except Exception:
                self.results.put((None, 'Refresh failed. Open Codex, then try again.'))
        self.worker = threading.Thread(target=work, daemon=False)
        self.worker.start()

    def apply_result(self, windows, error):
        self.busy = False
        self.refresh_button.config(state='normal')
        self.failed = error is not None
        if error:
            self.failures += 1
            self.state_label.config(text='Stale' if self.windows else 'Unavailable', fg=CORAL)
            self.detail_label.config(text=error, fg=CORAL)
        else:
            self.failures = 0
            self.windows = windows
            self.updated_at = time.time()
            self.state_label.config(text='Updated', fg=TEAL)
            self.updated_label.config(text='Updated ' + datetime.fromtimestamp(self.updated_at).strftime('%H:%M') + ' · 5 min')
        self.next_refresh = time.monotonic() + min(900, REFRESH_SECONDS * (2 ** min(self.failures, 2)))
        self.layout_content()
        self.render_countdown()
        self.draw_bar()
        self.root.after_idle(self.style_window)
        self.write_status()

    def render_countdown(self):
        windows = self.display_windows()
        if not windows:
            if self.failed:
                self.reset_label.config(text='Usage unavailable')
            return
        for index, window in enumerate(windows[:2]):
            row = self.rows[index]
            row['name'].config(text='Weekly' if window.minutes == 10080 else window.label)
            row['value'].config(text=percentage(window.remaining) + ' left')
            row['reset'].config(text=countdown(window.reset).replace('Resets in ', 'Reset in '))
        if not self.failed:
            expired = any(window.reset is not None and window.reset <= time.time() for window in windows)
            self.state_label.config(text='Refreshing' if self.busy else ('Awaiting update' if expired else 'Updated'),
                                    fg=MUTED if expired else TEAL)

    def tick(self):
        if self.closed:
            return
        try:
            windows, error = self.results.get_nowait()
            self.apply_result(windows, error)
        except queue.Empty:
            pass
        self.render_countdown()
        if self.auto_start and not self.busy:
            expired = next((w.reset for w in self.windows if w.reset and w.reset <= time.time() and w.reset not in self.expired_refetched), None)
            if expired:
                self.expired_refetched.add(expired)
            if expired or time.monotonic() >= self.next_refresh:
                self.refresh()
        self.root.after(1000, self.tick)

    def write_status(self):
        if self.status_path:
            try:
                self.root.update_idletasks()
                self.style_window()
                visible = [child for child in self.body.winfo_children() if child.winfo_manager()]
                clipped = any(child.winfo_y() + child.winfo_height() > self.body.winfo_height() or
                              child.winfo_x() + child.winfo_width() > self.body.winfo_width() for child in visible)
                save_preferences(self.status_path, {'version': VERSION, 'window_exists': bool(self.root.winfo_exists()),
                    'remaining': self.windows[0].remaining if self.windows else None,
                    'updated': self.updated_at, 'state': self.state_label.cget('text'), 'error': self.failed,
                    'width': self.root.winfo_width(), 'height': self.root.winfo_height(), 'layout_clipped': clipped,
                    'visible_limit_rows': len(self.windows), 'rounded_region_applied': self.rounding_applied,
                    'borderless': bool(self.root.overrideredirect()), 'alpha': self.root.attributes('-alpha')})
            except OSError:
                pass

    def persist(self):
        save_preferences(self.settings_path, {'x': self.root.winfo_x(), 'y': self.root.winfo_y(), 'topmost': self.topmost.get()})

    def toggle_topmost(self):
        self.root.attributes('-topmost', self.topmost.get())
        self.update_pin_text()
        try:
            self.persist()
        except OSError:
            self.state_label.config(text='Not saved', fg=CORAL)

    def open_menu(self, event=None):
        if event:
            x, y = event.x_root, event.y_root
        else:
            x, y = self.root.winfo_x() + 155, self.root.winfo_y() + self.root.winfo_height() - 55
        try:
            self.menu.tk_popup(x, y)
        finally:
            self.menu.grab_release()

    def reset_details(self):
        lines = []
        for window in self.display_windows():
            date = datetime.fromtimestamp(window.reset).astimezone().strftime('%a %d %b, %H:%M %Z') if window.reset else 'Unavailable'
            lines.append(f'{window.label}: {date}')
        messagebox.showinfo('Reset details', '\n'.join(lines) or 'No reset time is available yet.', parent=self.root)

    def about(self):
        messagebox.showinfo('Codex Usage Widget', f'Codex Usage Widget {VERSION}\nA Krēˈādiv Worx product.\nProduct direction: Raiden. Implementation: Codi.\n\nDrag the card to move it. Refresh: Ctrl+R. Close: Escape.\nPin keeps it above other windows. Menu shows reset details.\n\nReads the installed Codex CLI\'s existing sign-in every 5 minutes.\nNo model turns, reset credits, startup registration or analytics.\nOnly position and pin preference are saved.\n\nThe CLI protocol is experimental. Independent utility by Krēˈādiv Worx; not an official OpenAI application.', parent=self.root)

    def close(self):
        if self.closed:
            return
        self.closed = True
        self.cancel.set()
        try:
            self.persist()
        except OSError:
            pass
        self.root.destroy()


def smoke():
    with tempfile.TemporaryDirectory() as directory:
        root = tk.Tk()
        root.withdraw()
        widget = Widget(root, Path(directory) / "settings.json", auto_start=False)
        widget.apply_result([Window(95, 10080, int(time.time()) + 172800)], None)
        root.update_idletasks()
        assert widget.value_label.cget("text") == "95% left"
        assert widget.limit_label.cget("text") == "Weekly"
        assert widget.refresh_button.cget("state") == "normal"
        assert widget.bar.find_all()
        assert widget.rows[1]['frame'].winfo_manager() == ''
        widget.apply_result([Window(22, 10080, int(time.time()) + 86400), Window(72, 300, int(time.time()) + 7200)], None)
        assert widget.rows[0]['name'].cget('text') == '5-hour limit'
        assert widget.rows[0]['value'].cget('text') == '72% left'
        assert widget.rows[1]['name'].cget('text') == 'Weekly'
        assert widget.rows[1]['value'].cget('text') == '22% left'
        assert widget.rows[1]['frame'].winfo_manager() == 'place'
        widget.apply_result([Window(95, 10080, int(time.time()) + 172800)], None)
        assert widget.rows[1]['frame'].winfo_manager() == ''
        widget.apply_result(None, "Offline test")
        assert widget.value_label.cget("text") == "95% left"
        assert widget.state_label.cget("text") == "Stale"
        widget.topmost.set(True)
        widget.toggle_topmost()
        assert widget.pin_button.cget("text") == "Pinned"
        assert load_preferences(widget.settings_path)["topmost"] is True
        widget.close()
        print(json.dumps({"native_tk_smoke": "passed", "version": VERSION, "visual_review": "not automated"}))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--read-once", action="store_true")
    parser.add_argument("--status-file", type=Path)
    args = parser.parse_args()
    if args.smoke:
        smoke()
        return
    if args.read_once:
        print(json.dumps([{"remaining": w.remaining, "minutes": w.minutes, "reset": w.reset} for w in fetch_limits()]))
        return
    mutex = None
    if os.name == "nt":
        ctypes.windll.kernel32.CreateMutexW.restype = ctypes.c_void_p
        mutex = ctypes.windll.kernel32.CreateMutexW(None, False, "Local\\KreadivWorxCodexUsageWidget")
        if ctypes.windll.kernel32.GetLastError() == 183:
            return
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except (AttributeError, OSError):
            pass
    try:
        root = tk.Tk()
        settings = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "kreadiv-worx" / "CodexUsageWidget" / "settings.json"
        Widget(root, settings, args.status_file)
        root.mainloop()
    finally:
        if mutex:
            ctypes.windll.kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
            ctypes.windll.kernel32.CloseHandle(mutex)


if __name__ == "__main__":
    main()
