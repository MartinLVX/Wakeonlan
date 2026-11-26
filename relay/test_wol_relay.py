"""Pruebas del relay. Ejecutar con:  python3 -m unittest relay/test_wol_relay.py"""

import json
import sys
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wol_relay  # noqa: E402

TOKEN = "x" * 32


class MagicPacketTest(unittest.TestCase):
    def test_packet(self):
        p = wol_relay.build_magic_packet("01:23:45:67:89:ab")
        self.assertEqual(len(p), 102)
        self.assertEqual(p[:6], b"\xff" * 6)
        self.assertEqual(p[6:12], bytes.fromhex("0123456789AB"))
        self.assertEqual(p[-6:], bytes.fromhex("0123456789AB"))

    def test_mac_formats(self):
        for mac in ("01-23-45-67-89-AB", "0123456789ab", " 01:23:45:67:89:AB "):
            self.assertEqual(wol_relay.normalize_mac(mac), "0123456789AB")
        for bad in ("", "01:23:45:67:89", "zz:23:45:67:89:ab", "01:23:45:67:89:ab:cd"):
            with self.assertRaises(ValueError):
                wol_relay.normalize_mac(bad)

    def test_setup_link_keeps_secrets_in_fragment(self):
        link = wol_relay.setup_link("http://100.1.2.3:8787", "a b&c", "https://x.io/app/")
        self.assertTrue(link.startswith("https://x.io/app/#relay="))
        self.assertIn("token=a%20b%26c", link)


class ServerTest(unittest.TestCase):
    def setUp(self):
        self.sent = []
        cfg = wol_relay.default_config()
        cfg["token"] = TOKEN
        cfg["devices"][0]["check_host"] = "192.168.0.40"
        self.state = wol_relay.RelayState(cfg, wol_relay.find_pwa_dir())
        handler = wol_relay.make_handler(
            self.state,
            sender=lambda mac, bc, port: self.sent.append((mac, bc, port)),
            checker=lambda host, port: True,
        )
        handler.log_message = lambda *a: None
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()

    def request(self, path, method="GET", body=None, token=TOKEN, origin=None):
        req = urllib.request.Request(self.base + path, method=method)
        if token:
            req.add_header("Authorization", f"Bearer {token}")
        if origin:
            req.add_header("Origin", origin)
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, data) as r:
                return r.status, r.headers, r.read()
        except urllib.error.HTTPError as e:
            return e.code, e.headers, e.read()

    def test_requires_token(self):
        status, _, _ = self.request("/api/devices", token=None)
        self.assertEqual(status, 401)
        status, _, _ = self.request("/api/wake", "POST", {"id": "pc"}, token="mal")
        self.assertEqual(status, 401)
        self.assertEqual(self.sent, [])

    def test_lists_devices_without_mac(self):
        status, _, body = self.request("/api/devices")
        self.assertEqual(status, 200)
        devices = json.loads(body)["devices"]
        self.assertEqual(devices, [{"id": "pc", "name": "PC de escritorio", "has_status": True}])

    def test_wake(self):
        status, _, body = self.request("/api/wake", "POST", {"id": "pc"})
        self.assertEqual(status, 200, body)
        self.assertEqual(self.sent, [("AA:BB:CC:DD:EE:FF", "192.168.0.255", 9)])
        # Un segundo envío inmediato se rechaza.
        status, _, _ = self.request("/api/wake", "POST", {"id": "pc"})
        self.assertEqual(status, 429)

    def test_unknown_device(self):
        status, _, _ = self.request("/api/wake", "POST", {"id": "otro"})
        self.assertEqual(status, 404)

    def test_status(self):
        status, _, body = self.request("/api/status?id=pc")
        self.assertEqual(json.loads(body), {"id": "pc", "online": True})

    def test_lockout_after_failures(self):
        for _ in range(wol_relay.MAX_FAILURES):
            self.request("/api/devices", token="mal")
        status, _, _ = self.request("/api/devices")  # incluso con el token bueno
        self.assertEqual(status, 429)

    def test_cors_only_for_allowed_origins(self):
        _, headers, _ = self.request("/api/devices", origin="https://martinlvx.github.io")
        self.assertEqual(headers["Access-Control-Allow-Origin"], "https://martinlvx.github.io")
        _, headers, _ = self.request("/api/devices", origin="https://malo.example")
        self.assertIsNone(headers["Access-Control-Allow-Origin"])

    def test_serves_pwa_without_path_traversal(self):
        status, headers, body = self.request("/", token=None)
        self.assertEqual(status, 200)
        self.assertIn(b"<html", body)
        status, _, _ = self.request("/../relay/wol_relay.py", token=None)
        self.assertEqual(status, 404)
        status, _, _ = self.request("/%2e%2e/relay/wol_relay.py", token=None)
        self.assertEqual(status, 404)


if __name__ == "__main__":
    unittest.main()
