"""I6 — locale dictionaries served through one explicit, allowlisted route.

Locale is UI-only: it must never reach a verification request commitment or
a policy decision, and the route must never interpolate an arbitrary path.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_english_dictionary_loads():
    response = client.get("/ui/i18n/en.json")
    assert response.status_code == 200
    body = response.json()
    assert body["locale"] == "en"
    assert body["decision"]["CHALLENGE"] == "Additional verification needed"


def test_arabic_dictionary_loads_and_is_marked_draft():
    response = client.get("/ui/i18n/ar.json")
    assert response.status_code == 200
    body = response.json()
    assert body["locale"] == "ar"
    assert "review_status" in body, "an unreviewed translation must say so"


def test_an_unlisted_locale_is_rejected():
    response = client.get("/ui/i18n/fr.json")
    assert response.status_code in (404, 422)


def test_a_path_traversal_attempt_is_rejected_not_resolved():
    response = client.get("/ui/i18n/..%2f..%2fapp%2fconfig.json")
    assert response.status_code in (404, 400)


def test_both_dictionaries_share_the_same_keys():
    en = client.get("/ui/i18n/en.json").json()
    ar = client.get("/ui/i18n/ar.json").json()
    assert set(en["decision"]) == set(ar["decision"])
    assert set(en["chain_grade"]) == set(ar["chain_grade"])
    assert set(en["ui"]) == set(ar["ui"])
