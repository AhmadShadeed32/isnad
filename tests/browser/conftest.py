"""A real browser against a real server, in an isolated instance.

These tests exist because source-string assertions cannot answer the questions
that actually matter about a bilingual UI: does a result that was rendered in
English become Arabic when the reader switches, does a signed value survive the
switch byte-for-byte, does anything call the network that should not.

The server is a separate uvicorn process with every environment value stated
explicitly. The developer's `.env` carries a live provider, a live planner and a
real key; inheriting any of those would make a browser test bill someone.
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent.parent
BROWSER_KEY = "browser-test-key"
SHOTS = ROOT / "docs" / "ui" / "release"


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture(scope="module")
def server(tmp_path_factory):
    """One isolated instance per test file: its own port, database, signing key
    and merchant credential. Nothing it writes touches the developer's checkout.

    Per module rather than per session because this build keeps a small, evicted
    pool of demo credentials and a bounded set of event subscribers. A file that
    renders dozens of pages exhausts both, and the next file's journey then
    fails for a reason that has nothing to do with it.
    """
    workdir = tmp_path_factory.mktemp("browser-server")
    port = _free_port()
    env = {
        **os.environ,
        "ISNAD_PROVIDER": "mock",
        "ISNAD_PLANNER": "greedy",
        "ISNAD_GEMINI_API_KEY": "",
        "ISNAD_DEMO_MODE": "true",
        "ISNAD_DATABASE_URL": f"sqlite:///{workdir / 'browser.db'}",
        "ISNAD_VAULT_KEY_PATH": str(workdir / "vault.key"),
        "ISNAD_MERCHANT_API_KEYS": BROWSER_KEY,
        "ISNAD_SUBJECT_PEPPER": "browser-test-pepper",
        "ISNAD_RATE_LIMIT_ENABLED": "false",
        # The provider is the mock, so no operator is contacted. The value only
        # has to exist and be HTTPS for the network-conditions panel to be
        # reachable at all — creation is refused without one, by design.
        "ISNAD_NAC_CONGESTION_CALLBACK_URL": "https://callbacks.invalid/congestion",
    }
    process = subprocess.Popen(
        [
            sys.executable, "-m", "uvicorn", "app.main:app",
            "--host", "127.0.0.1", "--port", str(port),
            # As a deployment would, and --no-access-log because the OAuth code
            # and state are query parameters.
            "--workers", "1", "--no-access-log",
        ],
        cwd=ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    base = f"http://127.0.0.1:{port}"
    deadline = time.monotonic() + 40
    while time.monotonic() < deadline:
        if process.poll() is not None:
            output = process.stdout.read().decode("utf-8", "replace") if process.stdout else ""
            raise RuntimeError(f"the test server exited early:\n{output[-4000:]}")
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                break
        except OSError:
            time.sleep(0.2)
    else:
        process.kill()
        raise RuntimeError("the test server did not start in time")
    try:
        yield base
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:  # pragma: no cover - defensive
            process.kill()


# Own fixtures rather than the `pytest-playwright` plugin. That plugin installs
# a `pytest_runtest_call` wrapper with tryfirst=True, which runs ahead of
# pytest-asyncio's and leaves every `asyncio_mode = "auto"` coroutine test
# unawaited — 213 of this suite's tests turned into "Coroutine test ..." the
# moment it was installed. The sync API needs no plugin, and `pytest -q` stays
# one command.
@pytest.fixture
def browser():
    # Function-scoped, and the whole `sync_playwright()` context is exited with
    # it. Held open across the session, Playwright's sync API leaves a running
    # event loop in this thread and every later `asyncio_mode = "auto"` test in
    # the same process dies with "Runner.run() cannot be called from a running
    # event loop". Relaunching costs about a second per test; a suite that only
    # passes when it runs alone costs more.
    with sync_playwright() as playwright:
        instance = playwright.chromium.launch()
        try:
            yield instance
        finally:
            instance.close()


@pytest.fixture
def page(browser):
    context = browser.new_context()
    tab = context.new_page()
    tab.set_default_timeout(10000)
    try:
        yield tab
    finally:
        context.close()


@pytest.fixture
def problems(page):
    """Console errors and unhandled rejections, collected for every test.

    A page that looks right and throws is not a page that works, and the runbook
    asks for this explicitly rather than as an afterthought.
    """
    found: list[str] = []
    page.on("console", lambda m: found.append(f"{m.type}: {m.text}") if m.type == "error" else None)
    page.on("pageerror", lambda e: found.append(f"pageerror: {e}"))
    return found


@pytest.fixture
def judge(page, server):
    """The judge page, ready to drive.

    No credential to enter: the page is served with a short-TTL demo token
    minted server-side, and only while demo mode is on.
    """
    page.set_default_timeout(10000)
    page.goto(f"{server}/judge")
    page.wait_for_function("() => window.Isnad !== undefined", timeout=10000)
    page.wait_for_function(
        "() => { const b = document.getElementById('checkout'); return b && !b.disabled; }",
        timeout=15000,
    )
    return page


def shot(page, name: str) -> Path:
    """Save a release screenshot under a page-language-state-width name."""
    SHOTS.mkdir(parents=True, exist_ok=True)
    path = SHOTS / f"{name}.png"
    page.screenshot(path=str(path), full_page=True)
    return path
