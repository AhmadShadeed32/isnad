"""Read page-owned assets for the existing DOM/source regression checks.

This is only for static assertions and Node harnesses. Browser tests load the
real HTML and asset URLs, and test_ui_assets verifies the HTTP boundary itself.
Shared i18n stays external so per-page harnesses keep their explicit stubs.
"""
import re
from pathlib import Path

from app.ui import ASSETS


def expand_ui_source(html: str) -> str:
    def script(match):
        asset = ASSETS.get(match[1])
        return '<script>\n' + asset.read_text() + '\n</script>' if asset else match[0]

    def style(match):
        asset = ASSETS.get(match[1])
        return '<style>\n' + asset.read_text() + '\n</style>' if asset else match[0]

    html = re.sub(r'<script src="/ui/([^"]+)"></script>', script, html)
    return re.sub(r'<link rel="stylesheet" href="/ui/([^"]+)">', style, html)


def read_ui_source(path: Path) -> str:
    return expand_ui_source(path.read_text(encoding='utf-8'))


def fetch_ui_source(client, path: str) -> str:
    """A served page with its registered `/ui/` assets inlined.

    Markup and behaviour are one reviewable surface again, so a source
    assertion written before the split still tests what it was written to test.
    """
    return expand_ui_source(client.get(path).text)


def demo_token_from(html: str) -> str:
    """The per-render demo credential, read where the page now carries it.

    It moved out of a JavaScript string literal and into a meta tag when the
    scripts became static files: a cached asset cannot carry a per-request
    value, and the page body is the only part of the render that varies.
    """
    match = re.search(r'<meta name="isnad-demo-token" content="([^"]*)"', html)
    if match is None:
        raise AssertionError("the render carries no demo-token meta tag")
    return match[1]
