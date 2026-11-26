#!/usr/bin/env python3
"""Relay de Wake on LAN.

Un equipo siempre encendido en casa (hoy un Android con Termux, mañana una
Raspberry Pi) recibe una orden HTTP de la PWA y envía el paquete mágico por
UDP en la red local.

Solo usa la biblioteca estándar de Python 3.9+, así que funciona igual en
Termux, en Raspberry Pi OS y en cualquier Linux, macOS o Windows.

Uso:
    python3 wol_relay.py                 arranca el servidor (crea config.json la primera vez)
    python3 wol_relay.py --config RUTA   usa otro archivo de configuración
    python3 wol_relay.py link URL        muestra el enlace de configuración para la PWA

API (todas las rutas /api/* exigen la cabecera "Authorization: Bearer <token>"):
    GET  /api/devices            lista de equipos configurados
    POST /api/wake  {"id": "pc"} envía el paquete mágico a ese equipo
    GET  /api/status?id=pc       comprueba si el equipo responde (opcional)
"""

from __future__ import annotations

import argparse
import hmac
import json
import mimetypes
import os
import re
import secrets
import socket
import sys
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, urlsplit

HERE = Path(__file__).resolve().parent
DEFAULT_CONFIG = HERE / "config.json"
DEFAULT_PWA_URL = "https://martinlvx.github.io/Wakeonlan/"

MAC_RE = re.compile(r"^([0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}$|^[0-9A-Fa-f]{12}$")

# Protección contra fuerza bruta: tras MAX_FAILURES tokens erróneos desde una
# misma IP en FAILURE_WINDOW segundos, esa IP queda bloqueada ese tiempo.
MAX_FAILURES = 10
FAILURE_WINDOW = 15 * 60
# Tiempo mínimo entre dos envíos al mismo equipo.
WAKE_COOLDOWN = 3.0
MAX_BODY = 4096


# --------------------------------------------------------------------------
# Paquete mágico
# --------------------------------------------------------------------------

def normalize_mac(mac: str) -> str:
    mac = mac.strip()
    if not MAC_RE.match(mac):
        raise ValueError(f"MAC no válida: {mac!r}")
    return re.sub(r"[^0-9A-Fa-f]", "", mac).upper()


def build_magic_packet(mac: str) -> bytes:
    """6 bytes 0xFF seguidos de la MAC repetida 16 veces (102 bytes)."""
    raw = bytes.fromhex(normalize_mac(mac))
    return b"\xff" * 6 + raw * 16


def send_magic_packet(mac: str, broadcast: str = "255.255.255.255",
                      port: int = 9, repeats: int = 3) -> None:
    """Envía el paquete varias veces porque UDP no garantiza la entrega.

    Conviene usar la dirección de broadcast de la subred (por ejemplo
    192.168.0.255): 255.255.255.255 no siempre sale por el Wi-Fi cuando el
    Android tiene una VPN como Tailscale activa.
    """
    packet = build_magic_packet(mac)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        for i in range(repeats):
            sock.sendto(packet, (broadcast, port))
            if i < repeats - 1:
                time.sleep(0.1)


def is_reachable(host: str, port: int, timeout: float = 1.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


# --------------------------------------------------------------------------
# Configuración
# --------------------------------------------------------------------------

def default_config() -> dict:
    return {
        "bind": "0.0.0.0",
        "port": 8787,
        "token": secrets.token_urlsafe(32),
        "allowed_origins": ["https://martinlvx.github.io"],
        "serve_pwa": True,
        "devices": [
            {
                "id": "pc",
                "name": "PC de escritorio",
                "mac": "AA:BB:CC:DD:EE:FF",
                "broadcast": "192.168.0.255",
                "port": 9,
                "check_host": "",
                "check_port": 445,
            }
        ],
    }


def load_config(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        cfg = json.load(f)
    validate_config(cfg)
    return cfg


def validate_config(cfg: dict) -> None:
    token = cfg.get("token", "")
    if not isinstance(token, str) or len(token) < 16:
        raise ValueError('"token" debe tener al menos 16 caracteres')
    ids = set()
    for dev in cfg.get("devices", []):
        for key in ("id", "name", "mac"):
            if not dev.get(key):
                raise ValueError(f'Falta "{key}" en un equipo de "devices"')
        normalize_mac(dev["mac"])
        if dev["id"] in ids:
            raise ValueError(f'Id de equipo repetido: {dev["id"]}')
        ids.add(dev["id"])


def create_config(path: Path) -> dict:
    cfg = default_config()
    path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return cfg


def setup_link(relay_url: str, token: str, pwa_url: str = DEFAULT_PWA_URL) -> str:
    """Enlace que la PWA entiende para rellenarse sola.

    Los datos van después de "#", así que nunca se envían a ningún servidor.
    """
    return f"{pwa_url}#relay={quote(relay_url, safe='')}&token={quote(token, safe='')}"


def local_ips() -> list[str]:
    ips = set()
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))
            ips.add(s.getsockname()[0])
    except OSError:
        pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ips.add(info[4][0])
    except OSError:
        pass
    return sorted(ip for ip in ips if not ip.startswith("127."))


# --------------------------------------------------------------------------
# Servidor HTTP
# --------------------------------------------------------------------------

class RelayState:
    def __init__(self, cfg: dict, pwa_dir: Path | None):
        self.cfg = cfg
        self.pwa_dir = pwa_dir
        self.lock = threading.Lock()
        self.failures: dict[str, list[float]] = {}
        self.last_wake: dict[str, float] = {}

    def device(self, dev_id: str) -> dict | None:
        for dev in self.cfg.get("devices", []):
            if dev["id"] == dev_id:
                return dev
        return None

    def is_blocked(self, ip: str) -> bool:
        now = time.monotonic()
        with self.lock:
            recent = [t for t in self.failures.get(ip, []) if now - t < FAILURE_WINDOW]
            self.failures[ip] = recent
            return len(recent) >= MAX_FAILURES

    def record_failure(self, ip: str) -> None:
        with self.lock:
            self.failures.setdefault(ip, []).append(time.monotonic())

    def wake_allowed(self, dev_id: str) -> bool:
        now = time.monotonic()
        with self.lock:
            if now - self.last_wake.get(dev_id, -1e9) < WAKE_COOLDOWN:
                return False
            self.last_wake[dev_id] = now
            return True


def make_handler(state: RelayState, sender=send_magic_packet, checker=is_reachable):
    class Handler(BaseHTTPRequestHandler):
        server_version = "WolRelay/1.0"
        sys_version = ""

        # ---- utilidades ----
        def client_ip(self) -> str:
            # Detrás de Cloudflare Tunnel la IP real llega en esta cabecera.
            return self.headers.get("CF-Connecting-IP") or self.client_address[0]

        def cors_headers(self) -> None:
            origin = self.headers.get("Origin")
            allowed = state.cfg.get("allowed_origins", [])
            if origin and (origin in allowed or "*" in allowed):
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Vary", "Origin")
                self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
                self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
                self.send_header("Access-Control-Max-Age", "600")
                # Chrome pide esto cuando una web pública llama a una IP privada.
                self.send_header("Access-Control-Allow-Private-Network", "true")

        def send_json(self, status: int, data: dict) -> None:
            body = json.dumps(data, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.cors_headers()
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def authorized(self) -> bool:
            ip = self.client_ip()
            if state.is_blocked(ip):
                self.send_json(HTTPStatus.TOO_MANY_REQUESTS,
                               {"error": "Demasiados intentos fallidos. Espera 15 minutos."})
                return False
            header = self.headers.get("Authorization", "")
            token = header[7:] if header.startswith("Bearer ") else ""
            if not hmac.compare_digest(token.encode(), state.cfg["token"].encode()):
                state.record_failure(ip)
                self.log_message("token incorrecto desde %s", ip)
                self.send_json(HTTPStatus.UNAUTHORIZED, {"error": "Token incorrecto"})
                return False
            return True

        def log_message(self, fmt, *args):  # noqa: N802 (nombre de la clase base)
            sys.stderr.write("%s %s - %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"),
                                               self.client_ip(), fmt % args))

        # ---- métodos ----
        def do_OPTIONS(self):  # noqa: N802
            self.send_response(HTTPStatus.NO_CONTENT)
            self.cors_headers()
            self.send_header("Content-Length", "0")
            self.end_headers()

        def do_GET(self):  # noqa: N802
            url = urlsplit(self.path)
            if url.path == "/api/health":
                return self.send_json(HTTPStatus.OK, {"ok": True})
            if url.path == "/api/devices":
                if not self.authorized():
                    return
                devices = [{"id": d["id"], "name": d["name"],
                            "has_status": bool(d.get("check_host"))}
                           for d in state.cfg.get("devices", [])]
                return self.send_json(HTTPStatus.OK, {"devices": devices})
            if url.path == "/api/status":
                if not self.authorized():
                    return
                dev_id = parse_qs(url.query).get("id", [""])[0]
                dev = state.device(dev_id)
                if not dev:
                    return self.send_json(HTTPStatus.NOT_FOUND, {"error": "Equipo desconocido"})
                if not dev.get("check_host"):
                    return self.send_json(HTTPStatus.OK, {"id": dev_id, "online": None})
                online = checker(dev["check_host"], int(dev.get("check_port", 445)))
                return self.send_json(HTTPStatus.OK, {"id": dev_id, "online": online})
            if url.path.startswith("/api/"):
                return self.send_json(HTTPStatus.NOT_FOUND, {"error": "No existe"})
            return self.serve_static(url.path)

        def do_POST(self):  # noqa: N802
            url = urlsplit(self.path)
            if url.path != "/api/wake":
                return self.send_json(HTTPStatus.NOT_FOUND, {"error": "No existe"})
            if not self.authorized():
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                length = -1
            if length < 0 or length > MAX_BODY:
                return self.send_json(HTTPStatus.BAD_REQUEST, {"error": "Petición no válida"})
            try:
                data = json.loads(self.rfile.read(length) or b"{}")
                dev_id = str(data.get("id", ""))
            except (ValueError, AttributeError):
                return self.send_json(HTTPStatus.BAD_REQUEST, {"error": "JSON no válido"})
            dev = state.device(dev_id)
            if not dev:
                return self.send_json(HTTPStatus.NOT_FOUND, {"error": "Equipo desconocido"})
            if not state.wake_allowed(dev_id):
                return self.send_json(HTTPStatus.TOO_MANY_REQUESTS,
                                      {"error": "Espera unos segundos antes de volver a intentarlo"})
            try:
                sender(dev["mac"], dev.get("broadcast", "255.255.255.255"),
                       int(dev.get("port", 9)))
            except OSError as e:
                self.log_message("error enviando a %s: %s", dev_id, e)
                return self.send_json(HTTPStatus.INTERNAL_SERVER_ERROR,
                                      {"error": f"No se pudo enviar el paquete: {e}"})
            self.log_message("paquete mágico enviado a %s", dev_id)
            return self.send_json(HTTPStatus.OK, {"ok": True, "id": dev_id})

        # ---- PWA servida desde el propio relay (opcional) ----
        def serve_static(self, path: str):
            root = state.pwa_dir
            if not root or not state.cfg.get("serve_pwa", True):
                return self.send_json(HTTPStatus.NOT_FOUND, {"error": "No existe"})
            rel = path.lstrip("/") or "index.html"
            target = (root / rel).resolve()
            if root not in target.parents and target != root:
                return self.send_json(HTTPStatus.NOT_FOUND, {"error": "No existe"})
            if target.is_dir():
                target = target / "index.html"
            if not target.is_file():
                return self.send_json(HTTPStatus.NOT_FOUND, {"error": "No existe"})
            body = target.read_bytes()
            ctype = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
            if target.suffix == ".webmanifest":
                ctype = "application/manifest+json"
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-cache")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

    return Handler


def find_pwa_dir() -> Path | None:
    for candidate in (HERE / "pwa", HERE.parent / "pwa"):
        if (candidate / "index.html").is_file():
            return candidate.resolve()
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Relay de Wake on LAN")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    sub = parser.add_subparsers(dest="cmd")
    link = sub.add_parser("link", help="muestra el enlace de configuración de la PWA")
    link.add_argument("relay_url", help="URL con la que el celular llega al relay")
    link.add_argument("--pwa", default=DEFAULT_PWA_URL, help="URL de la PWA")
    args = parser.parse_args(argv)

    if not args.config.exists():
        create_config(args.config)
        print(f"Creé {args.config} con un token nuevo.")
        print("Ábrelo y pon la MAC y la dirección de broadcast de tu PC; luego vuelve a ejecutar.")
        return 0

    try:
        cfg = load_config(args.config)
    except (ValueError, json.JSONDecodeError) as e:
        print(f"Error en {args.config}: {e}", file=sys.stderr)
        return 1

    if args.cmd == "link":
        print(setup_link(args.relay_url.rstrip("/"), cfg["token"], args.pwa))
        return 0

    pwa_dir = find_pwa_dir()
    state = RelayState(cfg, pwa_dir)
    server = ThreadingHTTPServer((cfg.get("bind", "0.0.0.0"), int(cfg.get("port", 8787))),
                                 make_handler(state))
    port = server.server_address[1]
    print(f"Relay de Wake on LAN escuchando en el puerto {port}")
    for ip in local_ips():
        print(f"  http://{ip}:{port}")
    if pwa_dir and cfg.get("serve_pwa", True):
        print("La PWA también se sirve desde estas direcciones.")
    print("Para ver el enlace de configuración: python3 wol_relay.py link <URL del relay>")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
