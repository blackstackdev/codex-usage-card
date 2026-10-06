import io
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import widget


class NonClosingText(io.StringIO):
    def close(self):
        pass


class FakeProcess:
    def __init__(self, responses):
        self.stdin = NonClosingText()
        self.stdout = io.StringIO("".join(json.dumps(r) + "\n" for r in responses))
        self.stopped = False

    def poll(self):
        return 0 if self.stopped else None

    def terminate(self):
        self.stopped = True

    def kill(self):
        self.stopped = True

    def wait(self, timeout):
        return 0


class LimitsTests(unittest.TestCase):
    def test_remaining_clamps_and_rejects_non_numbers(self):
        self.assertEqual(widget.parse_window({"usedPercent": 5}).remaining, 95)
        self.assertEqual(widget.parse_window({"usedPercent": -4}).remaining, 100)
        self.assertEqual(widget.parse_window({"usedPercent": 140}).remaining, 0)
        for value in (None, True, "5", float("nan"), float("inf")):
            self.assertIsNone(widget.parse_window({"usedPercent": value}))

    def test_missing_reset_and_duration_are_unknown(self):
        window = widget.parse_window({"usedPercent": 5, "resetsAt": 1791783061000, "windowDurationMins": -1})
        self.assertIsNone(window.reset)
        self.assertIsNone(window.minutes)

    def test_primary_weekly_selection_and_short_window(self):
        snapshot = {"limitId": "codex", "primary": {"usedPercent": 8, "windowDurationMins": 300},
                    "secondary": {"usedPercent": 5, "windowDurationMins": 10080}}
        result = widget.parse_limits({"rateLimitsByLimitId": {"codex": snapshot, "other": {}}})
        self.assertEqual([w.label for w in result], ["Weekly limit", "5-hour limit"])
        self.assertEqual([w.remaining for w in result], [95, 92])

    def test_legacy_snapshot_is_supported(self):
        self.assertEqual(widget.parse_limits({"rateLimits": {"primary": {"usedPercent": 7}}})[0].remaining, 93)

    def test_unrelated_or_null_bucket_is_never_100_percent(self):
        for data in (None, {}, {"rateLimits": None}, {"rateLimits": {"limitId": "other", "primary": {"usedPercent": 0}}},
                     {"rateLimitsByLimitId": {"base_model_inference": {"primary": {"usedPercent": 0}}}}):
            with self.assertRaises(widget.UsageError):
                widget.parse_limits(data)

    def test_reset_never_infers_fresh_usage(self):
        self.assertIn("awaiting update", widget.countdown(99, now=100))
        self.assertEqual(widget.countdown(None), "Reset time unavailable")
        self.assertEqual(widget.countdown(100 + 5 * 86400 + 12 * 3600, now=100), "Resets in 5d 12h")
        self.assertEqual(widget.countdown(101, now=100), "Resets in 1m")

    def test_preferences_recover_and_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "prefs.json"
            self.assertEqual(widget.load_preferences(path), {})
            path.write_text("not json")
            self.assertEqual(widget.load_preferences(path), {})
            widget.save_preferences(path, {"x": 55, "y": 80, "topmost": True})
            self.assertEqual(widget.load_preferences(path), {"x": 55, "y": 80, "topmost": True})
            path.write_text(json.dumps({"token": "fictional", "topmost": False}))
            self.assertEqual(widget.load_preferences(path), {"topmost": False})

    def test_protocol_only_reads_usage_and_cleans_up(self):
        process = FakeProcess([{"id": 1, "result": {}}, {"method": "notification"},
                               {"id": 2, "result": {"rateLimits": {"primary": {"usedPercent": 5}}}}])
        with patch.object(widget.subprocess, "Popen", return_value=process):
            windows = widget.fetch_limits(executable="fictional-test.exe")
        methods = [json.loads(line)["method"] for line in process.stdin.getvalue().splitlines()]
        self.assertEqual(methods, ["initialize", "initialized", "account/rateLimits/read"])
        self.assertEqual(windows[0].remaining, 95)
        self.assertTrue(process.stopped)

    def test_server_errors_are_redacted(self):
        process = FakeProcess([{"id": 1, "error": {"message": "fictional-secret"}}])
        with patch.object(widget.subprocess, "Popen", return_value=process):
            with self.assertRaises(widget.UsageError) as caught:
                widget.fetch_limits(executable="fictional-test.exe")
        self.assertNotIn("fictional-secret", str(caught.exception))
        self.assertTrue(process.stopped)

    def test_cancel_and_closed_transport_cleanup(self):
        for cancel in (None, threading.Event()):
            if cancel is not None:
                cancel.set()
            process = FakeProcess([])
            with patch.object(widget.subprocess, "Popen", return_value=process):
                with self.assertRaises(widget.UsageError):
                    widget.fetch_limits(executable="fictional-test.exe", cancel=cancel)
            self.assertTrue(process.stopped)

    def test_percent_format(self):
        self.assertEqual(widget.percentage(94), "94%")
        self.assertEqual(widget.percentage(94.2), "94.2%")


if __name__ == "__main__":
    unittest.main()
