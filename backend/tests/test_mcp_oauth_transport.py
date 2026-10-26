"""Browser authorization through actual MCP HTTP initialize/list/call."""
import base64
import hashlib
import json
from datetime import timedelta
from urllib.parse import parse_qs, urlsplit

import pytest
from starlette.testclient import TestClient

import mcp_server
from app.models.user import User
from app.models.mcp_oauth import MCPOAuthGrant, MCPOAuthToken, now
from app.schemas.mcp_access_token import MCPAccessTokenCreate
from app.services.auth import create_access_token
from app.services.mcp_access_token import MCPAccessTokenService
from tests.conftest import TestingSessionLocal

RESOURCE = 'https://lifequest.example/mcp/http'
CALLBACK = 'https://chatgpt.example/connector/oauth/callback'
VERIFIER = 'v' * 64
CHALLENGE = base64.urlsafe_b64encode(hashlib.sha256(VERIFIER.encode()).digest()).rstrip(b'=').decode()


@pytest.fixture
def oauth_browser(client, monkeypatch, user):
    from app.config import settings
    for name, value in {'MCP_OAUTH_ENABLED': True, 'MCP_OAUTH_ISSUER_URL': 'https://lifequest.example', 'MCP_OAUTH_RESOURCE_URL': RESOURCE, 'MCP_OAUTH_FRONTEND_URL': 'https://lifequest.example/oauth/authorize'}.items():
        monkeypatch.setattr(settings, name, value)
    monkeypatch.setattr(mcp_server, 'SessionLocal', TestingSessionLocal)
    monkeypatch.setattr(mcp_server, '_db_initialized', True)
    saved = [(var, var.set(value)) for var, value in [(mcp_server._auth_user_id, None), (mcp_server._auth_token, None), (mcp_server._auth_token_authenticated, False)]]
    registration = client.post('/api/oauth/register', json={'client_name': 'ChatGPT test client', 'redirect_uris': [CALLBACK]}).json()
    headers = {'Authorization': 'Bearer ' + create_access_token({'sub': str(user.id)})}
    def begin():
        response = client.get('/api/oauth/authorize', params={'client_id': registration['client_id'], 'redirect_uri': CALLBACK, 'response_type': 'code', 'scope': 'mcp', 'resource': RESOURCE, 'state': 'state-from-client', 'code_challenge': CHALLENGE, 'code_challenge_method': 'S256'}, follow_redirects=False)
        assert response.status_code == 302, response.text
        assert response.headers['referrer-policy'] == 'no-referrer'
        return parse_qs(urlsplit(response.headers['location']).query)['request_id'][0]
    def issue(owner=None):
        owner = owner or user
        owner_headers = {'Authorization': 'Bearer ' + create_access_token({'sub': str(owner.id)})}
        handle = begin()
        details = client.get('/api/oauth/requests/' + handle, headers=owner_headers)
        assert details.status_code == 200, details.text
        assert details.json()['user_id'] == str(owner.id)
        approval = client.post('/api/oauth/consent', headers=owner_headers, json={'request_id': handle, 'approve': True})
        assert approval.status_code == 200, approval.text
        callback = approval.json()['redirect_uri']
        params = parse_qs(urlsplit(callback).query)
        assert params['state'] == ['state-from-client']
        response = client.post('/api/oauth/token', data={'grant_type': 'authorization_code', 'client_id': registration['client_id'], 'redirect_uri': CALLBACK, 'code': params['code'][0], 'resource': RESOURCE, 'code_verifier': VERIFIER})
        assert response.status_code == 200, response.text
        assert response.headers['cache-control'] == 'no-store'
        return response.json()
    try:
        yield {'client': client, 'user': user, 'headers': headers, 'registration': registration, 'begin': begin, 'issue': issue}
    finally:
        for var, token in reversed(saved):
            var.reset(token)


def auth(raw, session=None):
    headers = {'Authorization': 'Bearer ' + raw, 'Accept': 'application/json, text/event-stream'}
    if session:
        headers['Mcp-Session-Id'] = session
    return headers


def rpc(response):
    assert response.status_code == 200, response.text
    if response.headers.get('content-type', '').startswith('text/event-stream'):
        return json.loads(next(line[6:] for line in response.text.splitlines() if line.startswith('data: ')))
    return response.json()


def initialize(client, token):
    response = client.post('/http', headers=auth(token), json={'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {'protocolVersion': '2024-11-05', 'capabilities': {}, 'clientInfo': {'name': 'ChatGPT-test', 'version': '1'}}})
    assert rpc(response)['result']['serverInfo']['name'] == 'lifequest'
    session = response.headers['mcp-session-id']
    assert client.post('/http', headers=auth(token, session), json={'jsonrpc': '2.0', 'method': 'notifications/initialized'}).status_code == 202
    return session


def test_oauth_initialize_list_call_refresh_revoke(oauth_browser):
    b = oauth_browser
    token = b['issue']()
    with TestClient(mcp_server.create_http_app()) as mcp:
        unauthenticated = mcp.post('/http', json={})
        assert unauthenticated.status_code == 401
        assert 'resource_metadata="https://lifequest.example/.well-known/oauth-protected-resource/mcp/http"' in unauthenticated.headers['www-authenticate']
        metadata = mcp.get('/.well-known/oauth-protected-resource/mcp/http')
        assert metadata.status_code == 200
        assert metadata.json()['resource'] == RESOURCE
        session = initialize(mcp, token['access_token'])
        tools = rpc(mcp.post('/http', headers=auth(token['access_token'], session), json={'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list'}))['result']['tools']
        assert {'create_task', 'list_tasks', 'get_profile'} <= {t['name'] for t in tools}
        task = rpc(mcp.post('/http', headers=auth(token['access_token'], session), json={'jsonrpc': '2.0', 'id': 3, 'method': 'tools/call', 'params': {'name': 'create_task', 'arguments': {'title': 'OAuth isolated task'}}}))['result']
        assert not task.get('isError'), task
        assert 'OAuth isolated task' in str(task)
        assert 'password_hash' not in str(task)
        refresh = b['client'].post('/api/oauth/token', data={'grant_type': 'refresh_token', 'client_id': b['registration']['client_id'], 'refresh_token': token['refresh_token'], 'resource': RESOURCE})
        assert refresh.status_code == 200, refresh.text
        replacement = refresh.json()
        assert replacement['refresh_token'] != token['refresh_token']
        profile = rpc(mcp.post('/http', headers=auth(replacement['access_token'], session), json={'jsonrpc': '2.0', 'id': 4, 'method': 'tools/call', 'params': {'name': 'get_profile', 'arguments': {}}}))['result']
        assert not profile.get('isError'), profile
        assert str(b['user'].id) in str(profile)
        response = b['client'].post('/api/oauth/revoke', data={'client_id': b['registration']['client_id'], 'token': replacement['refresh_token']})
        assert response.status_code == 200
        for raw in (token['access_token'], replacement['access_token']):
            for method in ('initialize', 'tools/list', 'tools/call'):
                assert mcp.post('/http', headers=auth(raw, session), json={'jsonrpc': '2.0', 'id': 5, 'method': method}).status_code == 401


def test_consent_deny_csrf_and_cross_user_grants(oauth_browser, db_session):
    b = oauth_browser
    handle = b['begin']()
    assert b['client'].post('/api/oauth/consent', json={'request_id': handle, 'approve': True}).status_code == 401
    assert b['client'].post('/api/oauth/consent', headers=b['headers'], json={'request_id': handle, 'approve': True}).status_code == 403
    assert b['client'].get('/api/oauth/requests/' + handle, headers=b['headers']).status_code == 200
    second = User(username='oauth-other', email='oauth-other@example.com', password_hash='unused')
    db_session.add(second)
    db_session.commit()
    other_auth = {'Authorization': 'Bearer ' + create_access_token({'sub': str(second.id)})}
    assert b['client'].get('/api/oauth/requests/' + handle, headers=other_auth).status_code == 403
    assert b['client'].post('/api/oauth/consent', headers=other_auth, json={'request_id': handle, 'approve': True}).status_code == 403
    deny = b['client'].post('/api/oauth/consent', headers=b['headers'], json={'request_id': handle, 'approve': False})
    assert deny.status_code == 200
    params = parse_qs(urlsplit(deny.json()['redirect_uri']).query)
    assert params == {'state': ['state-from-client'], 'error': ['access_denied']}
    assert not db_session.query(MCPOAuthGrant).count()
    token = b['issue']()
    grants = b['client'].get('/api/oauth/grants', headers=b['headers']).json()
    assert len(grants) == 1
    assert b['client'].get('/api/oauth/grants', headers=other_auth).json() == []
    assert b['client'].delete('/api/oauth/grants/' + grants[0]['id'], headers=other_auth).status_code == 404
    with TestClient(mcp_server.create_http_app()) as mcp:
        session = initialize(mcp, token['access_token'])
        foreign = MCPAccessTokenService(db_session).create_token(second.id, MCPAccessTokenCreate(name='foreign'))[1]
        assert mcp.post('/http', headers=auth(foreign, session), json={}).status_code == 403
        own = MCPAccessTokenService(db_session).create_token(b['user'].id, MCPAccessTokenCreate(name='own'))[1]
        result = rpc(mcp.post('/http', headers=auth(own, session), json={'jsonrpc': '2.0', 'id': 3, 'method': 'tools/list'}))
        assert result['result']['tools']
        assert b['client'].delete('/api/oauth/grants/' + grants[0]['id'], headers=b['headers']).status_code == 200
        assert mcp.post('/http', headers=auth(token['access_token'], session), json={}).status_code == 401
        assert mcp.post('/http', headers=auth(own, session), json={'jsonrpc': '2.0', 'id': 4, 'method': 'tools/list'}).status_code == 200


def test_wrong_resource_refresh_token_jwt_and_expiry_cannot_initialize(oauth_browser, db_session, monkeypatch):
    b = oauth_browser
    token = b['issue']()
    with TestClient(mcp_server.create_http_app()) as mcp:
        for raw in (token['refresh_token'], b['headers']['Authorization'][7:]):
            assert mcp.post('/http', headers=auth(raw), json={}).status_code == 401
        assert mcp.post('/http?access_token=' + token['access_token'], json={}).status_code == 401
        grant = db_session.query(MCPOAuthGrant).one()
        grant.resource = 'https://unrelated.example/mcp'
        db_session.commit()
        assert mcp.post('/http', headers=auth(token['access_token']), json={}).status_code == 401
        grant.resource = RESOURCE
        db_session.commit()
        row = db_session.query(MCPOAuthToken).one()
        row.access_expires_at = now() - timedelta(seconds=1)
        db_session.commit()
        assert mcp.post('/http', headers=auth(token['access_token']), json={}).status_code == 401


def test_refresh_replay_revokes_mcp_immediately(oauth_browser):
    b = oauth_browser
    token = b['issue']()
    form = {'grant_type': 'refresh_token', 'client_id': b['registration']['client_id'], 'refresh_token': token['refresh_token']}
    replacement = b['client'].post('/api/oauth/token', data=form).json()
    with TestClient(mcp_server.create_http_app()) as mcp:
        session = initialize(mcp, replacement['access_token'])
        replay = b['client'].post('/api/oauth/token', data=form)
        assert replay.status_code == 400
        assert replay.json()['error'] == 'invalid_grant'
        assert mcp.post('/http', headers=auth(replacement['access_token'], session), json={}).status_code == 401


def test_bearer_scheme_is_case_insensitive(oauth_browser):
    token = oauth_browser['issue']()
    with TestClient(mcp_server.create_http_app()) as mcp:
        headers = auth(token['access_token'])
        headers['Authorization'] = headers['Authorization'].replace('Bearer ', 'bEaReR ')
        response = mcp.post('/http', headers=headers, json={'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {'protocolVersion': '2024-11-05', 'capabilities': {}, 'clientInfo': {'name': 'case-test', 'version': '1'}}})
        assert rpc(response)['result']['serverInfo']['name'] == 'lifequest'


def test_independent_oauth_users_cannot_read_or_modify_each_others_tasks(oauth_browser, db_session):
    b = oauth_browser
    second = User(username='oauth-data-other', email='oauth-data-other@example.com', password_hash='unused')
    db_session.add(second)
    db_session.commit()
    first = b['issue']()
    other = b['issue'](second)
    assert b['client'].get('/api/users/me', headers={'Authorization': 'Bearer ' + first['access_token']}).status_code == 401
    with TestClient(mcp_server.create_http_app()) as mcp:
        owner_session = initialize(mcp, first['access_token'])
        other_session = initialize(mcp, other['access_token'])
        created = rpc(mcp.post('/http', headers=auth(first['access_token'], owner_session), json={'jsonrpc': '2.0', 'id': 2, 'method': 'tools/call', 'params': {'name': 'create_task', 'arguments': {'title': 'Owner confidential task'}}}))['result']
        assert not created.get('isError'), created
        task = json.loads(created['content'][0]['text'])
        listed = rpc(mcp.post('/http', headers=auth(other['access_token'], other_session), json={'jsonrpc': '2.0', 'id': 3, 'method': 'tools/call', 'params': {'name': 'list_tasks', 'arguments': {}}}))['result']
        assert not listed.get('isError'), listed
        assert 'Owner confidential task' not in str(listed)
        for method, arguments in [('get_task', {'task_id': task['id']}), ('update_task', {'task_id': task['id'], 'title': 'Stolen'}), ('complete_task', {'task_id': task['id']})]:
            denied = rpc(mcp.post('/http', headers=auth(other['access_token'], other_session), json={'jsonrpc': '2.0', 'id': 4, 'method': 'tools/call', 'params': {'name': method, 'arguments': arguments}}))['result']
            assert denied.get('isError'), denied
        read = rpc(mcp.post('/http', headers=auth(first['access_token'], owner_session), json={'jsonrpc': '2.0', 'id': 5, 'method': 'tools/call', 'params': {'name': 'get_task', 'arguments': {'task_id': task['id']}}}))['result']
        assert 'Owner confidential task' in str(read)
        assert 'Stolen' not in str(read)


@pytest.mark.parametrize('path', ['/mcp/http', '/mcp/http/'])
def test_public_proxy_discovers_tools_without_redirects(oauth_browser, monkeypatch, path):
    """Exercise both real ASGI apps; emulate only the local TCP hop."""
    import httpx
    import app.main as main

    b = oauth_browser
    token = b['issue']()['access_token']
    real_async_client = httpx.AsyncClient
    with TestClient(mcp_server.create_http_app()) as upstream:
        def forward(request):
            response = upstream.request(request.method, str(request.url),
                                        headers=dict(request.headers), content=request.content,
                                        follow_redirects=False)
            return httpx.Response(response.status_code, headers=response.headers,
                                  content=response.content)

        def local_client(**kwargs):
            return real_async_client(transport=httpx.MockTransport(forward), **kwargs)

        monkeypatch.setattr(main.httpx, 'AsyncClient', local_client)
        browser = b['client']
        denied = browser.post(path, json={}, follow_redirects=False)
        assert denied.status_code == 401
        response = browser.post(path, headers=auth(token), follow_redirects=False,
                                json={'jsonrpc': '2.0', 'id': 1, 'method': 'initialize',
                                      'params': {'protocolVersion': '2024-11-05', 'capabilities': {},
                                                 'clientInfo': {'name': 'ChatGPT-proxy-test', 'version': '1'}}})
        assert response.status_code == 200, (response.status_code, response.headers.get('location'))
        assert 'location' not in response.headers
        assert rpc(response)['result']['serverInfo']['name'] == 'lifequest'
        session = response.headers['mcp-session-id']
        assert browser.post(path, headers=auth(token, session), follow_redirects=False,
                            json={'jsonrpc': '2.0', 'method': 'notifications/initialized'}).status_code == 202
        response = browser.post(path, headers=auth(token, session), follow_redirects=False,
                                json={'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list'})
        tools = rpc(response)['result']['tools']
        assert {'list_tasks', 'get_profile'} <= {tool['name'] for tool in tools}
        response = browser.post(path, headers=auth(token, session), follow_redirects=False,
                                json={'jsonrpc': '2.0', 'id': 3, 'method': 'tools/call',
                                      'params': {'name': 'get_profile', 'arguments': {}}})
        assert not rpc(response)['result'].get('isError')
        grant = browser.get('/api/oauth/grants', headers=b['headers']).json()[0]
        assert browser.delete('/api/oauth/grants/' + grant['id'], headers=b['headers']).status_code == 200
        assert browser.post(path, headers=auth(token, session), json={}, follow_redirects=False).status_code == 401
