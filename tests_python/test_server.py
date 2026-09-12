"""Test the local application's boundaries, not only its happy path."""
import json
from pathlib import Path
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from autopersona_py.server import ROOT, Workflow, make_handler


class LocalServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.flow = Workflow(ROOT, headless=True)
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(cls.flow))
        cls.url = "http://127.0.0.1:%d" % cls.httpd.server_port
        cls.flow.base_url = cls.url
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.flow.close()

    def test_environment_and_arbitrary_files_not_served(self):
        for path in ("/.env", "/media/.env", "/media/../.env", "/../.env", "/autopersona_py/planner.py"):
            with self.subTest(path=path), self.assertRaises(HTTPError) as caught:
                urlopen(self.url + path)
            self.assertEqual(caught.exception.code, 404)

    def test_cross_origin_requests_rejected(self):
        req = Request(self.url + "/api/prepare", data=b'{"input":{}}',
                      headers={"Content-Type": "application/json", "Origin": "https://example.com"})
        with self.assertRaises(HTTPError) as caught:
            urlopen(req)
        self.assertEqual(caught.exception.code, 403)

    def test_dns_rebinding_host_rejected(self):
        req = Request(self.url + "/api/state", headers={"Host": "evil.example"})
        with self.assertRaises(HTTPError) as caught:
            urlopen(req)
        self.assertEqual(caught.exception.code, 403)

    def test_publish_rejected_before_review(self):
        req = Request(self.url + "/api/publish", data=b'{"confirmation":"anything"}',
                      headers={"Content-Type": "application/json"})
        with self.assertRaises(HTTPError) as caught:
            urlopen(req)
        self.assertEqual(caught.exception.code, 400)
        self.assertIsNone(self.flow.browser)

    def test_state_does_not_expose_key(self):
        with urlopen(self.url + "/api/state") as response:
            body = json.load(response)
        self.assertNotIn("api_key", body["config"])
        self.assertNotIn("OPENAI_API_KEY", body["config"])
        self.assertIsInstance(body["config"]["api_configured"], bool)


if __name__ == "__main__":
    unittest.main()
