import os
import shutil
import socket
import subprocess
import time
from pathlib import Path


class Browser:

    def __init__(self, app, port=9222):
        self.profile_path = Path(
            app["profilePath"]
        ).expanduser().resolve()

        self.port = port
        self.chrome = None

    @property
    def cdp_url(self):
        return f"http://127.0.0.1:{self.port}"

    def open(self):
        self.profile_path.mkdir(
            parents=True,
            exist_ok=True
        )

        executable = os.getenv("BROWSER_EXECUTABLE")
        if executable:
            executable = shutil.which(executable) or executable
        else:
            executable = next(
                (
                    path
                    for name in ("google-chrome", "chromium", "chromium-browser")
                    if (path := shutil.which(name))
                ),
                None,
            )

        if not executable:
            raise RuntimeError(
                "No Chrome/Chromium executable found. Set BROWSER_EXECUTABLE "
                "in .env to its full path."
            )

        self.chrome = subprocess.Popen([
            executable,
            f"--remote-debugging-port={self.port}",
            f"--user-data-dir={self.profile_path}",
            "--no-first-run",
            "--no-default-browser-check",
            "about:blank"
        ])

        self.wait_until_ready()

    def wait_until_ready(self, timeout=15):
        end = time.time() + timeout

        while time.time() < end:
            if self.chrome.poll() is not None:
                raise RuntimeError(
                    f"Chrome exited with code {self.chrome.returncode}"
                )

            try:
                with socket.create_connection(
                    ("127.0.0.1", self.port),
                    timeout=0.5
                ):
                    return

            except OSError:
                time.sleep(0.2)

        raise RuntimeError(
            f"Chrome did not open CDP port {self.port}"
        )

    def close(self):
        if self.chrome and self.chrome.poll() is None:
            self.chrome.terminate()

            try:
                self.chrome.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.chrome.kill()
                self.chrome.wait()
