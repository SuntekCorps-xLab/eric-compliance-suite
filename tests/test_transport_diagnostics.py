from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading
import unittest
from unittest import mock

from scripts import detect

try:
    import requests
except ImportError:
    requests = None


@unittest.skipIf(requests is None, "Install requirements.txt for real HTTP transport tests")
class TransportDiagnosticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.seen = []
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                cls.seen.append(self.path)
                self.rfile.read(int(self.headers.get("Content-Length", 0)))
                self.send_response({"/html502": 502, "/json500": 500, "/rejected": 400, "/redirect": 302}.get(self.path, 200))
                if self.path == "/redirect":
                    self.send_header("Location", "/credential-target")
                self.end_headers()
                if self.path == "/rejected":
                    self.wfile.write(b'{"success":false,"code":4000001,"message":"invalid"}')
                elif self.path == "/json500":
                    self.wfile.write(b'{"detail":"PRIVATE-UPSTREAM-BODY"}')
                else:
                    self.wfile.write(b'<html>PRIVATE-UPSTREAM-BODY</html>')
            def log_message(self, *args):
                pass
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def test_http_status_and_error_kind_without_body_or_token_disclosure(self):
        for path, status, kind in (("html502", 502, "JSONDecodeError"), ("html200", 200, "JSONDecodeError"), ("json500", 500, "HTTPError")):
            with mock.patch.object(detect, "BASE", f"http://127.0.0.1:{self.server.server_port}"), mock.patch.dict("os.environ", {"NO_PROXY": "127.0.0.1"}):
                with self.assertRaises(detect.CLIError) as caught:
                    detect.api_call("test-token", path, {})
            message = str(caught.exception)
            self.assertIn(f"HTTP {status}", message)
            self.assertIn(kind, message)
            self.assertNotIn("test-token", message)
            self.assertNotIn("PRIVATE-UPSTREAM-BODY", message)

    def test_structured_http_error_is_preserved_and_redirect_is_not_followed(self):
        with mock.patch.object(detect, "BASE", f"http://127.0.0.1:{self.server.server_port}"), mock.patch.dict("os.environ", {"NO_PROXY": "127.0.0.1"}):
            self.assertEqual(detect.api_call("test-token", "rejected", {})["code"], 4000001)
            with self.assertRaisesRegex(detect.CLIError, "302.*重定向"):
                detect.api_call("test-token", "redirect", {})
        self.assertNotIn("/credential-target", self.seen)

    def test_timeout_connection_and_tls_errors_are_distinguishable_without_retry(self):
        for error in (requests.ReadTimeout("SECRET"), requests.ConnectTimeout("SECRET"), requests.ConnectionError("SECRET"), requests.exceptions.SSLError("SECRET")):
            with mock.patch.object(requests, "post", side_effect=error) as post:
                with self.assertRaises(detect.CLIError) as caught:
                    detect.api_call("SECRET", "fixed/path", {})
            message = str(caught.exception)
            self.assertIn(type(error).__name__, message)
            self.assertIn("未自动重试", message)
            self.assertNotIn("SECRET", message)
            self.assertEqual("服务端可能已完成并扣点" in message, isinstance(error, requests.exceptions.Timeout))
            post.assert_called_once()
