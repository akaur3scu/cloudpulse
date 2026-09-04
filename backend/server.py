"""Dependency-free local API and static server for CloudPulse."""

from __future__ import annotations

import json
import mimetypes
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from backend.monitor import check_endpoint, validate_url
from backend.storage import DuplicateEndpointError, Store

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_ROOT = PROJECT_ROOT / "frontend"
STORE = Store(os.getenv("CLOUDPULSE_DATABASE", str(PROJECT_ROOT / "cloudpulse.db")))


class CloudPulseHandler(BaseHTTPRequestHandler):
    server_version = "CloudPulse/1.0"

    def send_json(self, payload: object, status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def read_json(self) -> dict:
        try:
            length = int(self.headers.get("Content-Length", "0"))
            return json.loads(self.rfile.read(length) or b"{}")
        except (ValueError, json.JSONDecodeError) as error:
            raise ValueError("Request body must be valid JSON.") from error

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/api/health":
            self.send_json({"status": "ok"})
        elif path == "/api/endpoints":
            self.send_json({"services": STORE.list_services()})
        elif path.startswith("/api/"):
            self.send_json({"error": "Not found."}, 404)
        else:
            self.serve_static(path)

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        try:
            if path == "/api/endpoints":
                payload = self.read_json()
                name = str(payload.get("name", "")).strip()
                url = str(payload.get("url", "")).strip()
                if not name or len(name) > 80:
                    raise ValueError("Service name must be between 1 and 80 characters.")
                if len(STORE.get_endpoints()) >= 20:
                    raise ValueError("CloudPulse supports up to 20 monitors in this demo.")
                normalized_url = validate_url(url)
                endpoint = STORE.add_endpoint(name, normalized_url)
                STORE.add_check(endpoint["id"], check_endpoint(normalized_url))
                service = next(
                    item for item in STORE.list_services() if item["id"] == endpoint["id"]
                )
                self.send_json({"service": service}, 201)
            elif path == "/api/checks/run":
                for endpoint in STORE.get_endpoints():
                    STORE.add_check(endpoint["id"], check_endpoint(endpoint["url"]))
                self.send_json({"services": STORE.list_services()})
            else:
                self.send_json({"error": "Not found."}, 404)
        except DuplicateEndpointError as error:
            self.send_json({"error": str(error)}, 409)
        except ValueError as error:
            self.send_json({"error": str(error)}, 400)
        except Exception as error:
            self.log_error("Unhandled error: %s", error)
            self.send_json({"error": "The server could not complete the request."}, 500)

    def do_DELETE(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        prefix = "/api/endpoints/"
        if not path.startswith(prefix):
            self.send_json({"error": "Not found."}, 404)
            return
        endpoint_id = path.removeprefix(prefix)
        if STORE.delete_endpoint(endpoint_id):
            self.send_json({"deleted": endpoint_id})
        else:
            self.send_json({"error": "Monitor not found."}, 404)

    def serve_static(self, request_path: str) -> None:
        relative_path = "index.html" if request_path == "/" else request_path.lstrip("/")
        target = (FRONTEND_ROOT / relative_path).resolve()
        if FRONTEND_ROOT not in target.parents and target != FRONTEND_ROOT:
            self.send_error(403)
            return
        if not target.is_file():
            self.send_error(404)
            return
        body = target.read_bytes()
        content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def run(host: str = "127.0.0.1", port: int = 8000) -> None:
    server = ThreadingHTTPServer((host, port), CloudPulseHandler)
    print(f"CloudPulse is running at http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nCloudPulse stopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    run(port=int(os.getenv("PORT", "8000")))
