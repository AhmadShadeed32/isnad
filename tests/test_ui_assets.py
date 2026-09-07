"""The website's asset boundary: what is public, what is not, and what resolves.

Splitting the pages into markup plus `/ui/...` files made the browser fetch
things the tests used to read off disk. Two failure modes came with that, and
neither shows up in a source assertion: a reference that points at nothing
(the page loads, the behaviour is silently gone), and a lookup that reaches
past the registry into policy, recordings or source.
"""

from __future__ import annotations

import re

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.ui import ASSETS, PAGES, STATIC_ROOT

client = TestClient(app)

# Every asset the shipped markup actually asks the browser for.
REFERENCED = sorted(
    {
        match
        for page in PAGES
        for match in re.findall(
            r'(?:src|href)="/ui/([^"]+)"', (STATIC_ROOT / f"{page}.html").read_text("utf-8")
        )
    }
)


@pytest.mark.parametrize("asset_path", sorted(ASSETS))
def test_a_registered_asset_serves_its_file(asset_path: str):
    response = client.get(f"/ui/{asset_path}")

    assert response.status_code == 200
    assert response.text == ASSETS[asset_path].read_text("utf-8")
    expected = "text/css" if asset_path.endswith(".css") else "application/javascript"
    assert response.headers["content-type"].startswith(expected)
    # An asset is edited and the browser reloaded; a cached copy would make
    # that loop lie about what the page is running.
    assert response.headers["cache-control"] == "no-cache"


@pytest.mark.parametrize("reference", REFERENCED)
def test_every_asset_the_markup_references_resolves(reference: str):
    """A typo here 404s in the browser but still passes a source assertion,
    because the expander leaves an unknown reference untouched."""
    assert client.get(f"/ui/{reference}").status_code == 200


def test_the_shared_translation_script_stays_reachable():
    """`/ui/i18n.js` is served by the i18n router, not the asset registry, so
    it only resolves while that router is mounted ahead of the `/ui/{path}`
    catch-all in `create_app`. This is the test that notices a reorder."""
    assert "i18n.js" in REFERENCED
    assert client.get("/ui/i18n.js").status_code == 200


@pytest.mark.parametrize(
    "path",
    [
        "policy/policy.yaml",  # decision thresholds
        "console.html",  # markup carries a minted token
        "pages/consent_complete.js",  # registered for CSS only; no such file
        "../config.py",
        "../../pyproject.toml",
        "",
    ],
)
def test_an_unregistered_path_is_not_served(path: str):
    """The registry is an allowlist, so traversal is not a separate defence."""
    assert client.get(f"/ui/{path}").status_code in (404, 405)


def test_the_registry_only_names_files_that_exist():
    missing = [name for name, path in ASSETS.items() if not path.is_file()]

    assert not missing, f"registered but absent: {missing}"


def test_every_page_asset_on_disk_is_registered():
    """A file added under `pages/` that nothing registers is dead weight the
    next reader has to rule out."""
    orphans = [
        f"pages/{path.name}"
        for path in sorted((STATIC_ROOT / "pages").iterdir())
        if path.suffix in (".css", ".js") and f"pages/{path.name}" not in ASSETS
    ]

    assert not orphans, f"present but unregistered: {orphans}"


def test_a_page_name_outside_the_registry_is_refused():
    from app.ui import page_path

    assert page_path("judge") == STATIC_ROOT / "judge.html"
    with pytest.raises(ValueError):
        page_path("../config")
