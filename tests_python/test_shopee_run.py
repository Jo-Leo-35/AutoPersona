"""Verify runner continuation and single-submit behavior without network/browser."""
import argparse
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import shopee_run


class FakeBrowser:
    instances = []
    initial_phase = 'ready'
    submission_phase = 'published'

    def __init__(self, *args, **kwargs):
        self.calls = []
        self.options = kwargs
        self.page = self
        self.closed = False
        self.instances.append(self)

    def start(self, listing, mode, base_url, *, product_id=None):
        self.calls.append(('start', product_id, listing['sales']['stock']))
        return {'phase': self.initial_phase}

    def fill(self, listing):
        self.calls.append(('fill', listing['sales']['stock']))
        return {'phase': 'ready'}

    def publish(self, listing, title):
        self.calls.append(('publish', title))
        return {'phase': self.submission_phase, 'publishAttempted': True}

    def inspect(self):
        self.calls.append(('inspect',))
        return {'phase': 'published', 'publishAttempted': True}

    def close(self):
        self.closed = True

    def video_path(self):
        return None


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.input = self.folder / 'input.json'
        self.input.write_text(json.dumps({'product': {'title': '測試耳機'},
                                         'sales': {'price': 3990, 'stock': 1}}))
        FakeBrowser.instances = []
        FakeBrowser.initial_phase = 'ready'
        FakeBrowser.submission_phase = 'published'
        self.args = shopee_run.parser().parse_args(['--input', str(self.input),
                    '--product-id', '43834400022', '--run-dir', str(self.folder / 'run')])
        self.output = contextlib.redirect_stdout(io.StringIO())
        self.output.__enter__()
        self.addCleanup(self.output.__exit__, None, None, None)

    def test_existing_target_is_forwarded_and_fill_only_never_submits(self):
        self.assertEqual(shopee_run.run(self.args, FakeBrowser), 0)
        browser = FakeBrowser.instances[-1]
        self.assertEqual(browser.calls, [('start', '43834400022', 1)])
        self.assertTrue(browser.closed)
        report = json.loads((self.args.run_dir / 'report.json').read_text())
        self.assertFalse(report['submission_authorized'])
        self.assertEqual(report['operation'], 'update')
        self.assertGreaterEqual(report['elapsedSeconds'], 0)
        self.assertEqual(browser.options['slow_mo'], 0)
        self.assertFalse(browser.options['headless'])

    def test_recording_pacing_and_fullscreen_are_explicit(self):
        self.args.slow_mo = 150
        self.args.fullscreen = True
        self.assertEqual(shopee_run.run(self.args, FakeBrowser), 0)
        options = FakeBrowser.instances[-1].options
        self.assertEqual(options['slow_mo'], 150)
        self.assertTrue(options['fullscreen'])
        self.assertFalse(options['headless'])

    def test_observed_relist_operation_is_not_overwritten_as_update(self):
        self.args.publish = True
        with patch.object(FakeBrowser, 'publish', return_value={
                'phase': 'published', 'publishAttempted': True,
                'browser': {'operation': 'relist', 'completionVerified': True}}):
            self.assertEqual(shopee_run.run(self.args, FakeBrowser), 0)
        report = json.loads((self.args.run_dir / 'report.json').read_text())
        self.assertEqual(report['operation'], 'relist')

    def test_uncertain_submit_resumes_inspection_without_duplicate_submit(self):
        self.args.publish = True
        FakeBrowser.submission_phase = 'awaiting_browser'
        with patch('shopee_run.next_command', return_value={'action': 'resume'}):
            self.assertEqual(shopee_run.run(self.args, FakeBrowser), 0)
        self.assertEqual([c[0] for c in FakeBrowser.instances[-1].calls],
                         ['start', 'publish', 'inspect'])

    def test_answers_resume_same_browser_and_preserve_zero(self):
        self.args.publish = True
        FakeBrowser.initial_phase = 'awaiting_info'
        with patch('shopee_run.next_command', return_value={'answers': {'sales.stock': 0}}):
            self.assertEqual(shopee_run.run(self.args, FakeBrowser), 0)
        self.assertEqual(len(FakeBrowser.instances), 1)
        self.assertIn(('fill', 0), FakeBrowser.instances[0].calls)
        self.assertEqual(json.loads((self.args.run_dir / 'listing.json').read_text())['sales']['stock'], 0)

    def test_stale_control_signal_cannot_trigger_new_run(self):
        self.args.run_dir.mkdir()
        (self.args.run_dir / 'resume.json').write_text('{"action":"resume"}')
        with self.assertRaises(ValueError):
            shopee_run.run(self.args, FakeBrowser)
        self.assertFalse(FakeBrowser.instances)

    def test_product_id_rejects_url_or_non_numeric_target(self):
        for value in ('0', '../new', 'https://seller.shopee.tw/portal/product/1', '123?x=1'):
            with self.assertRaises(argparse.ArgumentTypeError):
                shopee_run.product_id(value)


if __name__ == '__main__':
    unittest.main()
