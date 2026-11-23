"""Exercise real HTTP routes and cookies using the standard-library client."""

import importlib.util
import json
import os
from http.cookiejar import CookieJar
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from urllib.error import HTTPError, URLError
from urllib.request import HTTPCookieProcessor, Request, build_opener


@unittest.skipUnless(all(importlib.util.find_spec(m) for m in ("uvicorn", "fastapi")),
                     "Install the backend requirements to exercise HTTP")
class HttpFlow(unittest.TestCase):
    def test_prediction_and_reveal_over_http(self):
        # Let the OS allocate the port inside the server process to avoid races.
        startup = """
import socket, sys, uvicorn
from pathlib import Path
sock = socket.socket()
sock.bind(('127.0.0.1', 0))
Path(sys.argv[1]).write_text(str(sock.getsockname()[1]))
uvicorn.Server(uvicorn.Config('backend.main:app', log_level='warning')).run(sockets=[sock])
"""
        with tempfile.TemporaryDirectory() as temp:
            port_file = Path(temp) / "port"
            proc = subprocess.Popen([sys.executable, "-c", startup, str(port_file)],
                                    env={**os.environ, "MISSING_SCRATCH_RUNTIME": temp,
                                         "MISSING_SCRATCH_COOKIE_SECURE": "0"})
            try:
                session = build_opener(HTTPCookieProcessor(CookieJar()))
                other = build_opener(HTTPCookieProcessor(CookieJar()))
                deadline = time.monotonic() + 15
                while time.monotonic() < deadline:
                    if proc.poll() is not None:
                        self.fail("Backend exited during startup")
                    if port_file.is_file() and (port := port_file.read_text()).isdigit():
                        origin = f"http://127.0.0.1:{port}"
                        try:
                            with session.open(origin + "/health", timeout=.5):
                                break
                        except (URLError, TimeoutError):
                            pass
                    time.sleep(.05)
                else:
                    self.fail("Timed out waiting for health")

                def call(path, body=None, client=session):
                    data = None if body is None else json.dumps(body).encode()
                    req = Request(origin+path, data=data, headers={"Content-Type": "application/json"})
                    try:
                        response = client.open(req, timeout=8)
                    except HTTPError as error:
                        response = error
                    with response:
                        data = response.read()
                        if response.headers.get_content_type() == "application/json":
                            data = json.loads(data)
                        return response.status, data

                for kind in ("visibility", "obstruction", "repair"):
                    status, task = call("/api/tasks/generate", {"kind": kind})
                    self.assertEqual(status, 200)
                    path = "/api/tasks/" + task["task_id"]
                    self.assertEqual(call(path + "/reveal")[0], 403)
                    self.assertEqual(call(path + "/reveal/image")[0], 403)
                    self.assertTrue(call(task["image_url"])[1].startswith(b"\x89PNG"))
                    invalid = "A" if kind == "visibility" else "VISIBLE"
                    self.assertEqual(call(path + "/predict", {"prediction": invalid})[0], 422)
                    for _ in range(2):
                        self.assertEqual(call(path + "/predict", {"prediction": task["options"][0]})[0], 200)
                    self.assertEqual(call(path + "/predict", {"prediction": task["options"][1]})[0], 409)
                    self.assertEqual(call(path + "/reveal", client=other)[0], 403)
                    status, reveal = call(path + "/reveal")
                    self.assertEqual(status, 200)
                    self.assertEqual(call(reveal["evidence"]["reveal_image_url"])[0], 200)

                status, pair = call("/api/tasks/generate-pair", {"kind": "repair"})
                self.assertEqual(status, 200)
                first, second = pair["tasks"]
                route = "/api/tasks/" + first["task_id"]
                self.assertEqual(call(route + "/predict", {"prediction": "A"})[0], 200)
                self.assertEqual(call(route + "/reveal")[0], 403)
                self.assertEqual(call("/api/tasks/" + second["task_id"] + "/predict", {"prediction": "B"})[0], 200)
                self.assertEqual(call(route + "/reveal")[0], 200)
            finally:
                if proc.poll() is None:
                    proc.terminate()
                proc.wait(timeout=8)
