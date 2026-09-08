import base64
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
import os
from pathlib import Path
import socket
import tempfile
import threading
import unittest
from unittest import mock

from scripts import detect, image_inputs as images
from test_detect import IMAGE, invoke


PUBLIC = (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.216.34", 80))
PNG = Path(IMAGE).read_bytes()


class ImageInputTests(unittest.TestCase):
    def test_missing_names_non_images_and_directories_never_reach_api(self):
        for command in ("d001", "l001", "c001", "p001"):
            for source in ("products", "logo", "test", "requirements.txt", "tests", "missing/image.png"):
                code, _, error, api = invoke([command, source])
                self.assertEqual(code, 1, error)
                api.assert_not_called()

    def test_small_valid_images_and_base64_with_slashes_remain_valid(self):
        self.assertLess(len(PNG), 100)
        self.assertEqual(base64.b64decode(images.load_image(IMAGE)), PNG)
        gif = base64.b64decode("R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7")
        for content in (PNG, gif, b"\xff\xd8\xff\xe0" + b"\x00" * 8 + b"\xff\xd9"):
            encoded = base64.b64encode(content).decode()
            self.assertEqual(images.load_image(encoded), encoded)

    def test_local_and_base64_size_caps_apply_before_encoding(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "large.png"
            path.write_bytes(PNG + b"x" * 100)
            with mock.patch.object(images, "MAX_IMAGE_BYTES", len(PNG)):
                self.assertEqual(base64.b64decode(images.load_image(IMAGE)), PNG)
                for source in (str(path), base64.b64encode(path.read_bytes()).decode()):
                    with self.assertRaises(images.ImageInputError):
                        images.load_image(source)

    def test_offline_urls_do_not_resolve_or_connect(self):
        with mock.patch.object(images.socket, "getaddrinfo", side_effect=AssertionError("DNS forbidden")), \
             mock.patch.object(images, "public_connection", side_effect=AssertionError("HTTP forbidden")):
            with self.assertRaisesRegex(images.ImageInputError, "离线模式"):
                images.load_image("https://example.com/image.png", offline=True)

    def test_all_resolved_addresses_must_be_public(self):
        blocked = ("127.0.0.1", "10.0.0.1", "172.16.0.1", "192.168.0.1", "169.254.169.254",
                   "100.64.0.1", "0.0.0.0", "224.0.0.1", "::1", "fe80::1", "fc00::1",
                   "::ffff:127.0.0.1", "64:ff9b::7f00:1", "2002:7f00:1::")
        for ip in blocked:
            address = (socket.AF_INET6 if ":" in ip else socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 80))
            for addresses in ([address], [PUBLIC, address]):
                with self.subTest(ip=ip), mock.patch.object(images.socket, "getaddrinfo", return_value=addresses), \
                     mock.patch.object(images, "public_connection") as connect:
                    with self.assertRaises(images.ImageInputError):
                        images.download_image("http://images.example.test/image.png")
                    connect.assert_not_called()

    def test_connection_pins_validated_address_and_keeps_tls_hostname(self):
        with mock.patch.object(images.socket, "socket") as create, \
             mock.patch.object(images.socket, "getaddrinfo", side_effect=AssertionError("Do not resolve again")), \
             mock.patch.object(images.ssl, "create_default_context") as context:
            connection = images.public_connection("images.example.test", 443, True, PUBLIC)
            create.return_value.connect.assert_called_once_with(PUBLIC[4])
            context.return_value.wrap_socket.assert_called_once_with(create.return_value, server_hostname="images.example.test")
            self.assertEqual(connection.auto_open, 0)
            connection.close()


class LocalImageServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.seen = []
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                cls.seen.append((self.path, dict(self.headers)))
                if self.path == "/redirect":
                    self.send_response(302)
                    self.send_header("Location", "http://127.0.0.1/secret")
                    self.end_headers()
                    return
                self.send_response(200)
                self.send_header("Content-Type", "text/html" if self.path == "/html" else "image/png")
                content = b"<html>PRIVATE-UPSTREAM-CONTENT</html>" if self.path in ("/html", "/fake.png") else PNG
                if self.path == "/large-declared":
                    self.send_header("Content-Length", str(40 * 1024 * 1024))
                if self.path == "/compressed":
                    self.send_header("Content-Encoding", "gzip")
                self.end_headers()
                self.wfile.write(content)
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

    def setUp(self):
        self.seen.clear()
        self.addresses = mock.patch.object(images, "public_addresses", return_value=[PUBLIC])
        self.connection = mock.patch.object(images, "public_connection", side_effect=lambda *args: http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=2))
        self.addresses.start()
        self.connection.start()
        self.addCleanup(self.addresses.stop)
        self.addCleanup(self.connection.stop)

    def test_real_http_download_encodes_image_without_forwarding_credentials(self):
        with mock.patch.dict(os.environ, {"ERIC_API_TOKEN": "private-token", "HTTP_PROXY": "http://invalid:9"}):
            content = images.load_image("http://images.example.test/image.png")
        self.assertEqual(base64.b64decode(content), PNG)
        self.assertEqual(len(self.seen), 1)
        for name in ("Token", "Authorization", "Cookie", "Proxy-Authorization"):
            self.assertNotIn(name, self.seen[0][1])

    def test_html_bad_magic_redirect_and_size_limits_block_detection(self):
        for path in ("/html", "/fake.png", "/redirect", "/large-declared", "/compressed"):
            code, _, error, api = invoke(["p001", "http://images.example.test" + path])
            self.assertEqual(code, 1, error)
            self.assertNotIn("PRIVATE-UPSTREAM-CONTENT", error)
            api.assert_not_called()
        self.assertNotIn("/secret", [path for path, _ in self.seen])
        with mock.patch.object(images, "MAX_IMAGE_BYTES", len(PNG) - 1):
            with self.assertRaisesRegex(images.ImageInputError, "20 MiB"):
                images.load_image("http://images.example.test/no-content-length")

    def test_signed_urls_and_network_errors_do_not_leak_details(self):
        for exc in (socket.gaierror("SECRET"), ssl_error(), TimeoutError("SECRET")):
            with mock.patch.object(images, "public_connection", side_effect=exc):
                with self.assertRaises(images.ImageInputError) as caught:
                    images.download_image("https://images.example.test/image.png?token=SECRET")
            self.assertNotIn("SECRET", str(caught.exception))


def ssl_error():
    import ssl
    return ssl.SSLError("SECRET")
