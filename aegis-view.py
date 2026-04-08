import json
import mimetypes
import time
import argparse
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse


def load_status(state_path):
    # Builds API payload from aegis.py's state file; adds server clock for the UI
    try:
        raw = state_path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, json.JSONDecodeError):
        data = {
            "log": str(state_path),
            "threshold": None,
            "window": None,
            "blocked": [],
            "recent_failures": [],
        }
    data["now"] = time.time()
    return data


def try_send_static(handler, static_root: Path) -> bool:
    # Serves a single file from static_root, e.g. /aegis-logo.png (no path traversal)
    static_root = static_root.resolve()
    rel = unquote(urlparse(handler.path).path).lstrip("/")
    if not rel or "/" in rel or rel.startswith(".") or ".." in rel:
        return False
    file_path = (static_root / rel).resolve()
    try:
        file_path.relative_to(static_root)
    except ValueError:
        return False
    if not file_path.is_file():
        return False
    mime, _ = mimetypes.guess_type(file_path.name)
    if not mime:
        mime = "application/octet-stream"
    data = file_path.read_bytes()
    handler.send_response(200)
    handler.send_header("Content-Type", mime)
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)
    return True


def run_server(port, state_path, html_path):
    # Serves dashboard, JSON, and same-folder images on 127.0.0.1 only
    try:
        html = html_path.read_bytes()
    except OSError:
        print(f"[!] Could not read '{html_path}'.")
        sys.exit(1)

    state_path = state_path.resolve()
    static_root = html_path.resolve().parent

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            return

        def do_GET(self):
            if self.path in ("/", "/index.html"):
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(html)
            elif self.path == "/api/status":
                payload = load_status(state_path)
                body = json.dumps(payload).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            elif try_send_static(self, static_root):
                pass
            else:
                self.send_error(404)

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"[*] Aegis view: http://127.0.0.1:{port}/")
    print(f"[*] Reading state from {state_path}")
    server.serve_forever()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="The Aegis view: localhost dashboard for aegis.py state."
    )
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=8765,
        help="Listen port (default: 8765)",
    )
    parser.add_argument(
        "-s",
        "--state",
        default="/tmp/aegis_state.json",
        help="State file written by aegis.py (default: /tmp/aegis_state.json)",
    )

    args = parser.parse_args()
    if args.port < 1 or args.port > 65535:
        print("[!] --port must be between 1 and 65535.")
        sys.exit(1)

    here = Path(__file__).resolve().parent
    html_path = here / "aegis.html"
    run_server(args.port, Path(args.state), html_path)
