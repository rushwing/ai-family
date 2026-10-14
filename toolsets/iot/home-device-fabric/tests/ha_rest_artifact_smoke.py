"""Installed HTTPX wire/deadline/TLS/close checks that remain effective under -O."""

import asyncio
import contextlib
import hashlib
import importlib.metadata
import json
import ssl
import subprocess
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from home_device_fabric.ha_configuration import HAConfiguration
from home_device_fabric.ha_rest import HARestClient, HARestError


def require(condition):
    if not condition:
        raise RuntimeError("installed_rest_check_failed")


@contextlib.contextmanager
def server(*, delay=0, tls=None):
    requests = []
    admitted = threading.Event()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            requests.append((self.command, self.path, dict(self.headers)))
            admitted.set()
            time.sleep(delay)
            try:
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"version":"2025.1.0","location_name":"private-house"}')
            except OSError:
                pass

        def log_message(self, *args):
            pass

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    httpd.daemon_threads = False
    if tls is not None:
        httpd.socket = tls.wrap_socket(httpd.socket, server_side=True)
    worker = threading.Thread(target=httpd.serve_forever, kwargs={"poll_interval": 0.01})
    worker.start()
    try:
        scheme = "https" if tls else "http"
        yield f"{scheme}://127.0.0.1:{httpd.server_port}", requests, admitted
    finally:
        httpd.shutdown()
        httpd.server_close()
        worker.join(timeout=2)
        require(not worker.is_alive())


def client(url, *, budget=10000):
    configuration = HAConfiguration(
        {"schema_version": 1, "base_url": url, "request_timeout_ms": budget},
        access_token="fictional-installed-credential",
    )
    return HARestClient(configuration)


async def error(operation, code, identity):
    try:
        await operation
    except HARestError as exc:
        require(exc.to_dict() == {"code": code, "correlation_id": identity, "http_status": None})
        require(exc.__context__ is None and exc.__cause__ is None)
        require(exc.args == (code,))
    else:
        raise RuntimeError("installed_rest_failure_not_rejected")


def main():
    with server() as (url, requests, admitted):
        async def success():
            wrapper = client(url)
            async with wrapper:
                result = await wrapper.runtime_info(correlation_id="installed-success")
                require(result.to_dict() == {"version": "2025.1.0"})
                require(repr(result) == "HARuntimeInfo(<redacted>)")
                require(repr(wrapper) == "HARestClient(<redacted>)")
            await wrapper.aclose()
            await error(wrapper.runtime_info(correlation_id="closed"), "client_closed", "closed")
        asyncio.run(success())
        require(len(requests) == 1)
        method, path, headers = requests[0]
        require(method == "GET" and path == "/api/config")
        require(headers["Authorization"] == "Bearer fictional-installed-credential")
        require(headers["Accept"] == "application/json")
        require(headers["Accept-Encoding"] == "identity" and "Cookie" not in headers)

    with server(delay=0.3) as (url, requests, admitted):
        async def timeout_and_close():
            wrapper = client(url, budget=150)
            active = asyncio.create_task(wrapper.runtime_info(correlation_id="deadline"))
            while not admitted.is_set() and not active.done():
                await asyncio.sleep(0.001)
            require(admitted.is_set())
            await error(wrapper.runtime_info(correlation_id="overlap"), "client_busy", "overlap")
            closing = asyncio.create_task(wrapper.aclose())
            await asyncio.sleep(0)
            await error(wrapper.runtime_info(correlation_id="closing"), "client_closed", "closing")
            await error(active, "timeout", "deadline")
            await closing
            require(not [t for t in asyncio.all_tasks() if t is not asyncio.current_task()])
        asyncio.run(timeout_and_close())
        require(len(requests) == 1)

    with tempfile.TemporaryDirectory(prefix="rest-tls-") as temporary:
        key, cert = Path(temporary) / "key.pem", Path(temporary) / "cert.pem"
        subprocess.run(
            ["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-keyout", str(key),
             "-out", str(cert), "-days", "1", "-subj", "/CN=localhost"],
            check=True, capture_output=True, timeout=20,
        )
        tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        tls.load_cert_chain(cert, key)
        with server(tls=tls) as (url, requests, admitted):
            async def tls_failure():
                async with client(url) as wrapper:
                    await error(wrapper.runtime_info(correlation_id="tls"),
                                "transport_failed", "tls")
            asyncio.run(tls_failure())
            require(requests == [])
    runtime_path = Path(sys.modules["home_device_fabric.ha_rest"].__file__)
    print(json.dumps({
        "python": sys.version, "optimized": not __debug__, "rest_smoke": "passed",
        "wire": True, "timeout": True, "tls_verification": True, "draining_close": True,
        "httpx": importlib.metadata.version("httpx"),
        "runtime_sha256": hashlib.sha256(runtime_path.read_bytes()).hexdigest(),
    }, sort_keys=True))


if __name__ == "__main__":
    main()
