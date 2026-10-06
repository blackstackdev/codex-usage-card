import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "codex-usage-card"
spec = importlib.util.spec_from_file_location("usage_helper", PLUGIN / "scripts" / "usage.py")
usage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(usage)

class PluginTests(unittest.TestCase):
    def test_snapshot_excludes_account_identity(self):
        with patch.object(usage.widget, "fetch_limits", return_value=[usage.widget.Window(72, 300, 1791783061)]):
            result, code = usage.run("status")
        self.assertEqual(code, 0)
        self.assertEqual(set(result), {"ok", "observed_at", "windows"})
        self.assertEqual(result["windows"], [{"remaining": 72, "minutes": 300, "reset": 1791783061}])

    def test_unexpected_error_is_redacted(self):
        with patch.object(usage.widget, "fetch_limits", side_effect=RuntimeError("secret@example.test")):
            result, code = usage.run("status")
        self.assertEqual(code, 1)
        self.assertNotIn("secret", json.dumps(result))

    def test_no_launch_for_invalid_action(self):
        with patch.object(usage.subprocess, "Popen") as launch:
            result, code = usage.run("open; unsafe")
        self.assertEqual(code, 2)
        launch.assert_not_called()

    def test_manifests_and_contained_assets(self):
        portable = json.loads((PLUGIN / "plugin.json").read_text(encoding="utf-8"))
        compatibility = json.loads((PLUGIN / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
        for key in ("name", "version", "description", "author"):
            self.assertEqual(portable[key], compatibility[key])
        self.assertEqual(portable["version"], usage.widget.VERSION)
        interface = portable["extensions"]["com.openai"]["interface"]
        self.assertEqual(interface, compatibility["interface"])
        self.assertLessEqual(len(interface["shortDescription"]), 30)
        for key in ("logo", "composerIcon"):
            path = (PLUGIN / interface[key]).resolve()
            self.assertTrue(path.is_relative_to(PLUGIN.resolve()))
            self.assertTrue(path.is_file())
        marketplace = json.loads((ROOT / ".agents" / "plugins" / "marketplace.json").read_text(encoding="utf-8"))
        self.assertEqual((ROOT / marketplace["plugins"][0]["source"]["path"]).resolve(), PLUGIN.resolve())

if __name__ == "__main__":
    unittest.main()
