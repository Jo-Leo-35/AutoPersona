"""Check recovery and script handoff across real workflow boundaries."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from autopersona_py.server import ROOT, Workflow, main


class WorkflowRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.flow = Workflow(Path(self.directory.name), headless=True, mode="demo")

    def tearDown(self):
        self.flow.close()
        self.directory.cleanup()

    def test_failed_new_preparation_cannot_reuse_previous_listing(self):
        self.flow.state.update(listing={"product": {"title": "old draft"}}, phase="ready")
        with patch("autopersona_py.planner.prepare_listing", side_effect=ValueError("invalid input")):
            self.flow.submit("prepare", {"input": {}})
            self.flow.tasks.join()
        state = self.flow.snapshot()
        self.assertEqual(state["phase"], "error")
        self.assertIsNone(state["listing"])
        self.assertFalse(state["busy"])
        with self.assertRaises(ValueError):
            self.flow.submit("start", {"mode": "demo"})

    def test_save_failure_does_not_kill_worker_or_strand_queue(self):
        prepared = {"listing": {"product": {"title": "draft"}}, "questions": [],
                    "warnings": [], "provider": {"mode": "offline"}}
        with patch("autopersona_py.planner.prepare_listing", return_value=prepared), \
                patch.object(self.flow, "_save", side_effect=OSError("disk unavailable")):
            for _ in range(2):
                self.flow.submit("prepare", {"input": {}})
                self.flow.tasks.join()
                self.assertTrue(self.flow.worker.is_alive())
                self.assertEqual(self.flow.snapshot()["phase"], "prepared")
                self.assertFalse(self.flow.snapshot()["busy"])

    def test_live_capture_follows_navigation_without_exposing_query_tokens(self):
        browser = Mock()
        browser.screenshot.return_value = b"png"
        browser.page.is_closed.return_value = False
        browser.page.url = "https://accounts.shopee.tw/seller/login?token=private#secret"
        browser.page.title.return_value = "登入蝦皮"
        self.flow.browser = browser
        self.flow._capture()
        state = self.flow.snapshot()
        self.assertEqual(state["browser"]["url"], "https://accounts.shopee.tw/seller/login")
        self.assertGreater(state["browser"]["screenshotCapturedAt"], 0)
        self.assertEqual(self.flow.latest_image, b"png")

    def test_answers_cannot_mutate_an_already_submitted_listing(self):
        self.flow.state.update(listing={"product": {"title": "submitted"}},
                               publishAttempted=True, phase="awaiting_browser")
        with self.assertRaises(ValueError):
            self.flow.submit("answers", {"answers": {"product.title": "different"}})
        self.assertEqual(self.flow.snapshot()["listing"]["product"]["title"], "submitted")


class ScriptHandoffTests(unittest.TestCase):
    def test_prepare_only_stdout_is_reusable_json(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(main(["--prepare-only", "--offline"]), 0)
        prepared = json.loads(output.getvalue())
        self.assertEqual(prepared["listing"]["research"]["matchedReviewCount"], 13)
        self.assertIsNone(prepared["listing"]["sales"]["price"])
        self.assertEqual(prepared["provider"]["mode"], "offline")
        from autopersona_py.planner import normalize_listing
        self.assertEqual(normalize_listing(prepared)["product"], prepared["listing"]["product"])

    def test_prepare_only_writes_output_without_starting_server(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "nested" / "listing.json"
            with patch("autopersona_py.server.Workflow") as workflow, contextlib.redirect_stderr(io.StringIO()):
                main(["--prepare-only", "--offline", "--output", str(target)])
                workflow.assert_not_called()
            self.assertIn("questions", json.loads(target.read_text(encoding="utf-8")))

    def test_invalid_input_fails_before_starting_worker(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "invalid.json"
            target.write_text("[]", encoding="utf-8")
            with patch("autopersona_py.server.Workflow") as workflow, \
                    contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as result:
                main(["--input", str(target), "--autostart"])
            self.assertEqual(result.exception.code, 2)
            workflow.assert_not_called()


if __name__ == "__main__":
    unittest.main()
