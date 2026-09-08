import pytest
from fastapi.testclient import TestClient

from app.agent.gemini import GeminiClient
from app.config import settings
from app.main import app

AUTH = {'Authorization': 'Bearer demo-merchant-key', 'X-Isnad-Planner': 'llm'}
PATH = '/v1/lab/run/clean_checkout'


@pytest.fixture
def model(monkeypatch):
    calls = []
    monkeypatch.setattr(settings, 'gemini_api_key', 'server-secret-test')
    def generate(client, **kwargs):
        calls.append(client._api_key)
        return {'action': 'stop', 'rationale': 'Model test response'}
    monkeypatch.setattr(GeminiClient, 'generate_json', generate)
    return calls


def test_server_key_runs_model_without_visitor_key(model):
    with TestClient(app) as client:
        response = client.post(PATH, headers=AUTH)
    assert response.status_code == 200
    assert model and set(model) == {'server-secret-test'}
    assert response.json()['provider'] == 'mock'
    assert 'server-secret-test' not in response.text
    assert response.json()['run']['receipt_ref'] is None


def test_lab_run_requires_auth_and_key(monkeypatch):
    monkeypatch.setattr(settings, 'gemini_api_key', '')
    with TestClient(app) as client:
        assert client.post(PATH).status_code == 401
        assert client.post(PATH, headers=AUTH).status_code == 400
        assert client.post('/v1/lab/run/unknown', headers=AUTH).status_code == 404


def test_lab_run_disabled_outside_demo(model, monkeypatch):
    monkeypatch.setattr(settings, 'demo_mode', False)
    with TestClient(app) as client:
        assert client.post(PATH, headers=AUTH).status_code == 403
    assert model == []


def test_public_configuration_reports_presence_never_secret(model):
    with TestClient(app) as client:
        response = client.get('/ui/settings.json')
    assert response.json()['server_gemini_available'] is True
    assert 'server-secret-test' not in response.text


def test_exhausted_site_budget_explains_quota_instead_of_asking_for_configuration(model, monkeypatch):
    from app import model_budget

    monkeypatch.setattr(model_budget, 'budget_exhausted', lambda: True)
    with TestClient(app) as client:
        response = client.post(PATH, headers=AUTH)
        assert response.status_code == 429
        assert 'allowance is used up' in response.json()['detail']
        assert model == []
        own_key = client.post(PATH, headers={**AUTH, 'X-Isnad-Gemini-Key': 'reviewer-test'})
        assert own_key.status_code == 200
        assert model == ['reviewer-test']
