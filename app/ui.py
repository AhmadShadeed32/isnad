"""Website file registry shared by page routes and the public asset endpoint.

Pages contain markup and per-request data. Only registered CSS/JavaScript files
are public assets; policy, recordings, HTML tokens and secrets are not mounted.
No bundler is needed: edit a file and reload the browser.
"""

from pathlib import Path

STATIC_ROOT = Path(__file__).parent / "static"
PAGES = ("judge", "console", "lab", "receipt", "proof", "privacy", "consent_complete")


def page_path(name: str) -> Path:
    if name not in PAGES:
        raise ValueError("Unknown UI page")
    return STATIC_ROOT / f"{name}.html"


ASSETS = {
    f"pages/{page}.{extension}": STATIC_ROOT / "pages" / f"{page}.{extension}"
    for page in PAGES
    for extension in ("css", "js")
    if extension == "css" or page != "consent_complete"
}
ASSETS["shared.css"] = STATIC_ROOT / "shared.css"

ASSETS["shared.js"] = STATIC_ROOT / "shared.js"
