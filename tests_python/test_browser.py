"""Browser outcome checks against the same local seller fixture used in the demo."""

import base64
import copy
import importlib.util
import tempfile
import threading
import unittest
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from autopersona_py.browser import BrowserSession


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "autopersona_py" / "web"
PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aNwAAAABJRU5ErkJggg==")


class ImageBoundaryTests(unittest.TestCase):
    def test_only_real_images_inside_project_are_uploadable(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            root = Path(directory)
            session = BrowserSession(root, headless=True)
            (root / "product.png").write_bytes(PNG)
            self.assertEqual(session._image_files(["product.png"]), [str((root / "product.png").resolve())])
            (root / ".env").write_text("local private configuration", encoding="utf-8")
            (root / "pretend.png").write_text("not image bytes", encoding="utf-8")
            (Path(outside) / "outside.png").write_bytes(PNG)
            (root / "linked.png").symlink_to(Path(outside) / "outside.png")
            for path in (".env", "pretend.png", "linked.png", str(Path(outside) / "outside.png")):
                with self.subTest(path=path), self.assertRaises(ValueError):
                    session._image_files([path])

    def test_publication_requires_exact_title_before_any_browser_operation(self):
        session = BrowserSession(ROOT, headless=True)
        result = session.publish({"product": {"title": "商品 A"}}, "商品A")
        self.assertEqual(result["phase"], "awaiting_info")
        self.assertFalse(result["publishAttempted"])


@unittest.skipUnless(importlib.util.find_spec("playwright"), "Install Python Playwright for browser integration")
class SellerBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not (WEB / "demo-seller.html").is_file():
            raise unittest.SkipTest("The local seller fixture has not been installed")

        class Handler(SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=str(WEB), **kwargs)

            def do_GET(self):
                if self.path == "/demo/seller":
                    self.path = "/demo-seller.html"
                super().do_GET()

            def log_message(self, *args):
                pass

        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base_url = "http://127.0.0.1:" + str(cls.server.server_port)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def test_page_question_resume_and_confirmed_publish_once(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "product.png").write_bytes(PNG)
            listing = {
                "product": {"title": "可見瀏覽器測試商品", "categoryPath": ["影音", "麥克風"],
                            "brand": "測試品牌", "model": "TEST-1", "condition": "used"},
                "content": {"description": "適合社區活動主持的麥克風，內容由測試提供。"},
                "compliance": {},
                "sales": {"price": 1999, "stock": 2},
                "shipping": {"weightKg": 0.3, "packageSizeCm": {"width": 20, "length": 30, "height": 10}, "dangerousGoods": False},
                "media": {"imagePaths": ["product.png"]},
            }
            events = []
            session = BrowserSession(root, emit=lambda kind, message: events.append(message), headless=True, slow_mo=0,
                                     record_video_dir=root / "recordings")
            try:
                result = session.start(listing, "demo", self.base_url)
                self.assertEqual(result["phase"], "awaiting_info", result)
                page_question = next(q for q in result["questions"] if q["path"] == "compliance.connectionType")
                self.assertEqual(page_question["type"], "select")
                self.assertEqual({o["value"] for o in page_question["options"]}, {"wired", "wireless"})
                self.assertFalse(session.page.is_closed())
                self.assertIn("media.imagePaths", result["filled"])
                self.assertFalse(session._success_visible())

                completed = copy.deepcopy(listing)
                completed["compliance"]["connectionType"] = "wired"
                result = session.fill(completed)
                self.assertEqual(result["phase"], "ready", result)
                self.assertEqual(result["questions"], [])
                self.assertTrue(session.screenshot().startswith(b"\x89PNG"))
                self.assertFalse(session._success_visible())
                self.assertTrue(any("連接" in event or "連線" in event for event in events))

                result = session.publish(completed, "confirm")
                self.assertFalse(result["publishAttempted"])
                self.assertFalse(session._success_visible())
                changed = copy.deepcopy(completed)
                changed["sales"]["price"] = 2500
                self.assertEqual(session.publish(changed, changed["product"]["title"])["phase"], "awaiting_info")
                self.assertEqual(session.fill(changed)["phase"], "ready")
                self.assertEqual(session.page.locator('[data-field="sales.price"]').input_value(), "2500")
                result = session.publish(changed, changed["product"]["title"])
                self.assertEqual(result["phase"], "published", result)
                self.assertTrue(result["publishAttempted"])
                self.assertEqual(session.publish(changed, changed["product"]["title"])["phase"], "published")
                self.assertEqual(session.page.locator('[data-testid="published-success"]:visible').count(), 1)

                # Exercise the observed Shopee picker contract without visiting
                # or mutating any real seller page.
                picker = '''<button id="open" onclick="document.querySelector('[role=dialog]').hidden=false">請選擇商品分類</button>
                <div role="dialog" hidden><h2>編輯分類</h2>
                <button onclick="document.getElementById('leaf').hidden=false">影音</button>
                <button id="leaf" hidden>耳機/耳麥/藍牙耳機</button>
                <button onclick="window.confirmed=(window.confirmed||0)+1;this.parentElement.hidden=true;document.getElementById('breadcrumb').textContent='影音 > 耳機/耳麥/藍牙耳機'">Confirm</button>
                </div><div id="breadcrumb"></div>'''
                session.mode = "shopee"
                session.page.set_content(picker)
                self.assertFalse(session._choose_category(["影音", "不存在的分類"]))
                self.assertEqual(session.page.evaluate("window.confirmed || 0"), 0)
                session.page.set_content(picker)
                self.assertTrue(session._choose_category(["影音", "耳機/耳麥/藍牙耳機"]))
                self.assertEqual(session.page.evaluate("window.confirmed"), 1)
            finally:
                session.close()
            video = session.video_path()
            self.assertIsNotNone(video)
            self.assertTrue(Path(video).is_file())
            self.assertGreater(Path(video).stat().st_size, 0)


if __name__ == "__main__":
    unittest.main()
