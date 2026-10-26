"""OAuth discovery and HTTP contracts using isolated API fixtures."""
import pytest


@pytest.fixture
def oauth_enabled(monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, 'MCP_OAUTH_ENABLED', True, raising=False)
    monkeypatch.setattr(settings, 'MCP_OAUTH_ISSUER_URL', 'https://lifequest.example', raising=False)
    monkeypatch.setattr(settings, 'MCP_OAUTH_RESOURCE_URL', 'https://lifequest.example/mcp/http', raising=False)
    monkeypatch.setattr(settings, 'MCP_OAUTH_FRONTEND_URL', 'https://lifequest.example/oauth/authorize', raising=False)
    return settings


def test_authorization_server_discovery(client, oauth_enabled):
    response = client.get('/.well-known/oauth-authorization-server', headers={'Host': 'attacker.example'})
    assert response.status_code == 200
    data = response.json()
    assert data['issuer'] == 'https://lifequest.example'
    assert data['authorization_endpoint'] == 'https://lifequest.example/api/oauth/authorize'
    assert data['token_endpoint'] == 'https://lifequest.example/api/oauth/token'
    assert data['registration_endpoint'] == 'https://lifequest.example/api/oauth/register'
    assert data['revocation_endpoint'] == 'https://lifequest.example/api/oauth/revoke'
    assert data['code_challenge_methods_supported'] == ['S256']
    assert set(data['grant_types_supported']) == {'authorization_code', 'refresh_token'}
    assert 'attacker.example' not in response.text
    assert 'implicit' not in response.text


@pytest.mark.parametrize('path', ['/.well-known/oauth-protected-resource', '/.well-known/oauth-protected-resource/mcp/http'])
def test_protected_resource_discovery(client, oauth_enabled, path):
    response = client.get(path)
    assert response.status_code == 200
    assert response.json()['resource'] == oauth_enabled.MCP_OAUTH_RESOURCE_URL
    assert response.json()['authorization_servers'] == [oauth_enabled.MCP_OAUTH_ISSUER_URL]
    assert response.json()['bearer_methods_supported'] == ['header']
    assert response.json()['scopes_supported'] == ['mcp']


def test_oauth_disabled_exposes_no_issuer(client):
    assert client.get('/.well-known/oauth-authorization-server').status_code == 404
    assert client.post('/api/oauth/register', json={'redirect_uris': ['https://chatgpt.example/callback']}).status_code == 404


def test_oauth_user_endpoints_require_ordinary_login(client, oauth_enabled):
    for method, path, body in [('GET', '/api/oauth/requests/unknown', None), ('POST', '/api/oauth/consent', {'request_id': 'unknown', 'approve': True}), ('GET', '/api/oauth/grants', None), ('DELETE', '/api/oauth/grants/00000000-0000-0000-0000-000000000000', None)]:
        assert client.request(method, path, json=body).status_code == 401


def test_token_protocol_error_is_not_fastapi_validation_error(client, oauth_enabled):
    registration = client.post('/api/oauth/register', json={'redirect_uris': ['https://chatgpt.example/callback']}).json()
    response = client.post('/api/oauth/token', data={'grant_type': 'password', 'client_id': registration['client_id']})
    assert response.status_code == 400
    assert response.json()['error'] in ('invalid_request', 'unsupported_grant_type', 'invalid_client')
    assert response.headers['cache-control'] == 'no-store'
    assert response.headers['pragma'] == 'no-cache'


def test_authorization_errors_return_to_exact_registered_callback(client, oauth_enabled):
    import base64
    import hashlib
    from urllib.parse import parse_qs, urlsplit
    registered = client.post('/api/oauth/register', json={'redirect_uris': ['https://chatgpt.example/callback?tenant=life%20quest']}).json()
    params = {'client_id': registered['client_id'], 'redirect_uri': 'https://chatgpt.example/callback?tenant=life%20quest', 'response_type': 'code', 'scope': 'admin', 'resource': oauth_enabled.MCP_OAUTH_RESOURCE_URL, 'state': 'client-state', 'code_challenge_method': 'S256', 'code_challenge': base64.urlsafe_b64encode(hashlib.sha256(b'v' * 64).digest()).rstrip(b'=').decode()}
    response = client.get('/api/oauth/authorize', params=params, follow_redirects=False)
    assert response.status_code == 302
    assert response.headers['location'].startswith(params['redirect_uri'] + '&')
    assert parse_qs(urlsplit(response.headers['location']).query) == {'tenant': ['life quest'], 'state': ['client-state'], 'error': ['invalid_scope'], 'error_description': ['Only mcp scope is supported']}
    params['redirect_uri'] = 'https://attacker.example/callback'
    response = client.get('/api/oauth/authorize', params=params, follow_redirects=False)
    assert response.status_code == 400
    assert 'location' not in response.headers


def test_duplicate_parameters_and_large_body_are_protocol_errors(client, oauth_enabled):
    response = client.post('/api/oauth/token', content='client_id=x&client_id=y&grant_type=refresh_token', headers={'Content-Type': 'application/x-www-form-urlencoded'})
    assert response.status_code == 400
    assert response.json()['error'] == 'invalid_request'
    response = client.post('/api/oauth/register', content='x' * 17000, headers={'Content-Type': 'application/json'})
    assert response.status_code == 400
    assert response.json()['error'] == 'invalid_request'
    response = client.get('/api/oauth/authorize?client_id=x&client_id=y', follow_redirects=False)
    assert response.status_code == 400
    assert 'location' not in response.headers


def test_registration_is_rate_limited_and_map_bounded(client, oauth_enabled, monkeypatch):
    from collections import defaultdict, deque
    import app.api.mcp_oauth as api
    monkeypatch.setattr(api, '_registration_windows', defaultdict(deque))
    for _ in range(30):
        assert client.post('/api/oauth/register', json={}).status_code == 400
    assert client.post('/api/oauth/register', json={}).status_code == 429
    assert len(api._registration_windows) == 1


@pytest.mark.parametrize('issuer', ['http://lifequest.example', 'https://user:pass@lifequest.example', 'https://lifequest.example/path', 'https://lifequest.example/#fragment', 'https://lifequest.example?x=1', '//lifequest.example', 'https://lifequest.example\\evil'])
def test_unsafe_oauth_configuration_rejected(oauth_enabled, issuer):
    from app.oauth_config import get_oauth_config
    oauth_enabled.MCP_OAUTH_ISSUER_URL = issuer
    with pytest.raises(ValueError):
        get_oauth_config()
