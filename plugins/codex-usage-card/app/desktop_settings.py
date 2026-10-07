"""Bounded local sizing and per-user Windows startup registration."""
from pathlib import Path
import ctypes
import json
import os
import shutil
import sys

MIN_WIDTH, MAX_WIDTH, DEFAULT_WIDTH = 360, 960, 480
STARTUP_MARKER = "' KreadivWorx Codex Cosmic startup v1"


def windows_folder(csidl, fallback):
    # Codex can redirect LOCALAPPDATA. Prefer Windows' configured location;
    # installed copies additionally anchor their settings to their app folder.
    if os.name == 'nt':
        folder = ctypes.create_unicode_buffer(32768)
        if ctypes.windll.shell32.SHGetFolderPathW(None,csidl,None,0,folder) == 0:
            return Path(folder.value)
    return Path(fallback)


def local_data_root():
    if os.name == 'nt':
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                r'Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders') as key:
                value,_ = winreg.QueryValueEx(key,'Local AppData')
                return Path(os.path.expandvars(value))
        except OSError:
            pass
    return windows_folder(0x1c,os.environ.get('LOCALAPPDATA',str(Path.home())))


def settings_file(source=None):
    source = Path(source or Path(__file__).resolve().parent)
    if source.name == 'app' and source.parent.name == 'CodexUsageCosmic':
        return source.parent/'settings.json'
    return local_data_root()/'kreadiv-worx/CodexUsageCosmic/settings.json'


def card_size(width, screen_width=MAX_WIDTH, screen_height=640):
    maximum = max(MIN_WIDTH, min(MAX_WIDTH, int(screen_width), int(screen_height * 1.5)))
    if not isinstance(width, (int, float)) or isinstance(width, bool):
        width = DEFAULT_WIDTH
    try:
        width = int(width)
    except (ValueError, OverflowError):
        width = DEFAULT_WIDTH
    width = max(MIN_WIDTH, min(width, maximum))
    return width, round(width * 2 / 3)


def read_size(path, screen_width=MAX_WIDTH, screen_height=640):
    try:
        if path.stat().st_size > 4096:
            return card_size(DEFAULT_WIDTH, screen_width, screen_height)
        data = json.loads(path.read_text(encoding='utf-8'))
        return card_size(data.get('width') if isinstance(data, dict) else None,
                         screen_width, screen_height)
    except (OSError, ValueError):
        return card_size(DEFAULT_WIDTH, screen_width, screen_height)


def resized_ppm(data, width, height):
    """Resize the bundled artwork using standard-library nearest sampling."""
    magic, dimensions, maximum, pixels = bytes(data).split(b'\n', 3)
    if magic != b'P6' or maximum != b'255':
        raise ValueError('Unsupported Tk image data')
    source_width, source_height = map(int, dimensions.split())
    if len(pixels) != source_width * source_height * 3:
        raise ValueError('Incomplete Tk image data')
    offsets = [min(source_width-1, int(x * source_width / width))*3 for x in range(width)]
    rows = []
    for y in range(height):
        start = min(source_height-1, int(y * source_height / height))*source_width*3
        row = pixels[start:start+source_width*3]
        rows.append(b''.join(row[x:x+3] for x in offsets))
    return f'P6\n{width} {height}\n255\n'.encode('ascii') + b''.join(rows)


class Startup:
    def __init__(self, source=None, startup_path=None, install_root=None, pythonw=None):
        self.source = Path(source or Path(__file__).resolve().parent)
        self.path = Path(startup_path or windows_folder(7,Path(os.environ['APPDATA']) /
            'Microsoft/Windows/Start Menu/Programs/Startup') / 'Kreadiv Worx Cosmic Usage.vbs')
        current_install = self.source if self.source.name == 'app' and self.source.parent.name == 'CodexUsageCosmic' else None
        self.install_root = Path(install_root or current_install or local_data_root() /
                                'kreadiv-worx/CodexUsageCosmic/app')
        self.pythonw = Path(pythonw or Path(sys.executable).with_name('pythonw.exe'))

    def owned(self):
        try:
            if self.path.stat().st_size > 4096:
                return False
            content = self.path.read_bytes()
            encoding = 'utf-16' if content.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig'
            return content.decode(encoding).startswith(STARTUP_MARKER)
        except (OSError, UnicodeError):
            return False

    def enabled(self):
        return self.owned()

    def enable(self):
        if self.path.exists() and not self.owned():
            raise OSError('A different startup entry uses this name; it was preserved.')
        if not self.pythonw.is_file():
            raise OSError('Python for Windows was not found; startup was not enabled.')
        self.install_root.mkdir(parents=True, exist_ok=True)
        files = ['cosmic.py', 'usage_core.py', 'desktop_settings.py', 'VERSION', 'LICENSE',
                 'README.md', 'VERIFICATION.md', 'CHANGELOG.md', 'Launch Cosmic.vbs', 'assets/cosmic-background.png',
                 'assets/cosmic-original.png', 'assets/studio-mark.png']
        for filename in files:
            source = self.source / filename
            target = self.install_root / filename
            if source.resolve() != target.resolve():
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
        # Absolute quoted paths avoid PATH/startup working-directory assumptions.
        command = f'"{self.pythonw.resolve()}" "{self.install_root.resolve() / "cosmic.py"}"'
        literal = command.replace('"', '""')
        script = STARTUP_MARKER + '\nOption Explicit\nCreateObject("WScript.Shell").Run "' + literal + '", 0, False\n'
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix('.tmp')
        # Windows Script Host accepts Unicode UTF-16, not a UTF-8 BOM.
        temp.write_text(script, encoding='utf-16')
        temp.replace(self.path)

    def disable(self):
        if self.path.exists() and not self.owned():
            raise OSError('A different startup entry uses this name; it was preserved.')
        if self.owned():
            self.path.unlink()
