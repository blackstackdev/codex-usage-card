import tempfile
from pathlib import Path
import unittest
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from desktop_settings import Startup, STARTUP_MARKER, card_size, read_size, resized_ppm, settings_file


class DesktopSettingsTests(unittest.TestCase):
    def test_installed_settings_ignore_launch_environment(self):
        installed = Path('Stable App Root')/'CodexUsageCosmic'/'app'
        self.assertEqual(settings_file(installed),installed.parent/'settings.json')
    def test_bad_and_extreme_sizes(self):
        for bad in (None,True,float('nan'),float('inf'),'900'):
            self.assertEqual(card_size(bad),(480,320))
        self.assertEqual(card_size(1),(360,240))
        self.assertEqual(card_size(9000),(960,640))
        self.assertEqual(card_size(9000,800,480),(720,480))

    def test_size_reloads_and_bad_preferences_recover(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'settings.json'
            self.assertEqual(read_size(path),(480,320))
            path.write_text('{"width":720,"x":25,"topmost":true}')
            self.assertEqual(read_size(path),(720,480))
            path.write_text('[]')
            self.assertEqual(read_size(path),(480,320))

    def test_ppm_preserves_source_colours_and_dimensions(self):
        source = b'P6\n2 1\n255\n'+bytes((255,0,0,0,0,255))
        resized = resized_ppm(source,4,2)
        self.assertEqual(resized,b'P6\n4 2\n255\n'+bytes((255,0,0,255,0,0,0,0,255,0,0,255))*2)

    def test_startup_stable_install_quotes_paths_and_removes_only_own_entry(self):
        with tempfile.TemporaryDirectory(prefix='cosmic QA ') as directory:
            root=Path(directory)
            runtime=root/'pythonw.exe'
            runtime.touch()
            startup=Startup(source=Path(__file__).resolve().parents[1],startup_path=root/'Startup'/'Cosmic.vbs',
                            install_root=root/'Stable App',pythonw=runtime)
            startup.enable()
            self.assertTrue(startup.enabled())
            self.assertTrue((startup.install_root/'desktop_settings.py').exists())
            self.assertEqual(startup.path.read_bytes()[:2],b'\xff\xfe')
            text=startup.path.read_text(encoding='utf-16')
            self.assertTrue(text.startswith(STARTUP_MARKER))
            self.assertIn('""'+str(runtime.resolve())+'""',text)
            self.assertIn(str(startup.install_root.resolve()/'cosmic.py'),text)
            self.assertIn(', 0, False',text)
            startup.enable()
            startup.disable()
            self.assertFalse(startup.path.exists())
            startup.path.write_text('Other startup program')
            with self.assertRaises(OSError): startup.enable()
            with self.assertRaises(OSError): startup.disable()
            self.assertEqual(startup.path.read_text(),'Other startup program')


if __name__ == '__main__': unittest.main()
