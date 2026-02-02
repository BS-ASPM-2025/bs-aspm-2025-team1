"""
Fixtures for browser-based UI tests.
Starts a live uvicorn server for Playwright to test against.
"""

import os
import subprocess
import time
import urllib.request

import pytest


BROWSER_TEST_PORT = 8765
BASE_URL = f"http://127.0.0.1:{BROWSER_TEST_PORT}"


def _wait_for_server(url: str, timeout: float = 15.0) -> bool:
    """Poll until the server responds or timeout."""
    start = time.monotonic()
    while time.monotonic() - start < timeout:
        try:
            urllib.request.urlopen(url, timeout=2)
            return True
        except (urllib.error.URLError, OSError):
            time.sleep(0.3)
    return False


@pytest.fixture(scope="session")
def live_server():
    """
    Start uvicorn in a subprocess for the duration of the browser test session.
    Uses a test database to avoid polluting the main DB.
    """
    proc = subprocess.Popen(
        ["uvicorn", "app:app", "--host", "127.0.0.1", "--port", str(BROWSER_TEST_PORT)],
        cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        if not _wait_for_server(BASE_URL):
            proc.kill()
            proc.wait()
            pytest.skip("Live server did not start in time")
        yield BASE_URL
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


@pytest.fixture(scope="session")
def base_url(live_server):
    """Base URL for the running app."""
    return live_server
