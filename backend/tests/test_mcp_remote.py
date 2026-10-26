"""Remote protocol/security checks against isolated test state."""
import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from mcp.server.lowlevel.server import request_ctx
from starlette.testclient import TestClient
import mcp_server
from app.models.user import User
from app.models.mcp_access_token import MCPAccessToken
from app.schemas.mcp_access_token import MCPAccessTokenCreate
from app.services.mcp_access_token import MCPAccessTokenService


@pytest.fixture
def remote_db(database, monkeypatch):
    monkeypatch.setattr(mcp_server, 'SessionLocal', lambda: database)
    monkeypatch.setattr(mcp_server, '_db_initialized', True)
    saved = [(var, var.set(value)) for var, value in [(mcp_server._auth_user_id, None), (mcp_server._auth_token, None), (mcp_server._auth_token_authenticated, False)]]
    users = [User(username=f'remote-{i}', email=f'remote-{i}@example.com', password_hash='unused') for i in range(2)]
    database.add_all(users)
    database.commit()
    tokens = [MCPAccessTokenService(database).create_token(u.id, MCPAccessTokenCreate(name='remote'))[1] for u in users]
    try:
        yield database, users, tokens
    finally:
        for var, token in reversed(saved):
            var.reset(token)


def headers(token, session=None):
    result = {'Authorization': f'Bearer {token}', 'Accept': 'application/json, text/event-stream'}
    if session:
        result['Mcp-Session-Id'] = session
    return result


def rpc(response):
    response.raise_for_status()
    if response.headers.get('content-type', '').startswith('text/event-stream'):
        return json.loads(next(line[6:] for line in response.text.splitlines() if line.startswith('data: ')))
    return response.json()


def test_streamable_http_real_protocol_and_isolation(remote_db, monkeypatch):
    db, users, tokens = remote_db
    monkeypatch.setenv('LIFEQUEST_MCP_TOKEN', tokens[0])
    with TestClient(mcp_server.create_http_app()) as client:
        assert client.post('/http', json={}).status_code == 401
        response = client.post('/http', headers=headers(tokens[0]), json={'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {'protocolVersion': '2024-11-05', 'capabilities': {}, 'clientInfo': {'name': 'test', 'version': '1'}}})
        assert rpc(response)['result']['serverInfo']['name'] == 'lifequest'
        session = response.headers['mcp-session-id']
        auth = headers(tokens[0], session)
        assert client.post('/http', headers=auth, json={'jsonrpc': '2.0', 'method': 'notifications/initialized'}).status_code == 202
        tools = rpc(client.post('/http', headers=auth, json={'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list'}))['result']['tools']
        assert {'create_task', 'get_profile'} <= {t['name'] for t in tools}
        for number, name, arguments in [(3, 'create_task', {'title': 'remote task'}), (4, 'list_tasks', {})]:
            result = rpc(client.post('/http', headers=auth, json={'jsonrpc': '2.0', 'id': number, 'method': 'tools/call', 'params': {'name': name, 'arguments': arguments}}))['result']
            assert not result.get('isError'), result
            assert 'remote task' in str(result)
            assert 'password_hash' not in str(result)
        assert client.post('/http', headers=headers(tokens[1], session), json={'jsonrpc': '2.0', 'id': 5, 'method': 'tools/list'}).status_code == 403
        assert client.delete('/http', headers={'Mcp-Session-Id': session}).status_code == 401
        row = db.query(MCPAccessToken).filter_by(token_prefix=tokens[0][:16]).one()
        row.revoked_at = datetime.now(timezone.utc)
        db.commit()
        assert client.post('/http', headers=auth, json={}).status_code == 401


def test_login_token_session_revalidates(remote_db):
    db, users, tokens = remote_db
    class Session:
        pass
    context = request_ctx.set(SimpleNamespace(session=Session()))
    try:
        assert mcp_server.login_with_token(tokens[0])['status'] == 'ok'
        assert mcp_server.get_profile()['id'] == str(users[0].id)
        row = db.query(MCPAccessToken).filter_by(token_prefix=tokens[0][:16]).one()
        row.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.commit()
        with pytest.raises(RuntimeError, match='Token'):
            mcp_server.get_profile()
    finally:
        request_ctx.reset(context)


def test_remote_never_falls_back_to_environment_token(remote_db, monkeypatch):
    db, users, tokens = remote_db
    monkeypatch.setenv('LIFEQUEST_MCP_TOKEN', tokens[0])
    from starlette.requests import Request
    context = request_ctx.set(SimpleNamespace(session=None, request=Request({'type': 'http', 'headers': []})))
    try:
        with pytest.raises(RuntimeError):
            mcp_server._resolve_user_id(db)
    finally:
        request_ctx.reset(context)


@pytest.mark.parametrize('method', ['POST', 'GET', 'DELETE'])
def test_api_streamable_proxy_forwards_protocol_headers(client, monkeypatch, method):
    import httpx
    import app.main as main
    seen = []
    real_client = httpx.AsyncClient

    def upstream(request):
        seen.append(request)
        return httpx.Response(200, headers={'Mcp-Session-Id': 'test-session', 'Content-Type': 'application/json'}, json={'ok': True})

    monkeypatch.setattr(main.httpx, 'AsyncClient', lambda **kwargs: real_client(transport=httpx.MockTransport(upstream), **kwargs))
    response = client.request(method, '/mcp/http', content=b'{}', headers={'Authorization': 'Bearer test', 'Mcp-Session-Id': 'test-session', 'MCP-Protocol-Version': '2024-11-05', 'Accept': 'application/json, text/event-stream'})
    assert response.status_code == 200
    assert response.headers['mcp-session-id'] == 'test-session'
    assert seen[0].url.path == '/http/'
    assert seen[0].method == method
    assert seen[0].headers['authorization'] == 'Bearer test'
    assert seen[0].headers['mcp-protocol-version'] == '2024-11-05'


def test_sse_query_session_cannot_be_masked_by_http_session_header(remote_db):
    from starlette.responses import JSONResponse
    db, users, tokens = remote_db
    async def endpoint(scope, receive, send):
        await JSONResponse({'ok': True})(scope, receive, send)
    wrapped = mcp_server.MCPTokenAuthMiddleware(endpoint)
    session_id = 'a' * 32
    wrapped.session_users[session_id] = users[0].id
    client = TestClient(wrapped)
    response = client.post(f'/messages/?session_id={session_id}', headers={'Authorization': f'Bearer {tokens[1]}', 'Mcp-Session-Id': 'unrelated'})
    client.close()
    assert response.status_code == 403


@pytest.mark.parametrize('form', ['hex', 'hyphen', 'uppercase', 'braces'])
def test_sse_session_id_alias_cannot_skip_auth(remote_db, form):
    from uuid import UUID
    from starlette.responses import JSONResponse
    _, users, tokens = remote_db
    async def endpoint(scope, receive, send):
        await JSONResponse({'ok': True})(scope, receive, send)
    wrapped = mcp_server.MCPTokenAuthMiddleware(endpoint)
    value = UUID('12345678-1234-5678-abcd-123456789abc')
    wrapped.session_users[value.hex] = users[0].id
    session_id = {'hex': value.hex, 'hyphen': str(value), 'uppercase': str(value).upper(), 'braces': '{' + str(value) + '}'}[form]
    client = TestClient(wrapped)
    assert client.post(f'/messages/?session_id={session_id}').status_code == 401
    assert client.post(f'/messages/?session_id={session_id}', headers=headers(tokens[1])).status_code == 403
    client.close()


@pytest.mark.parametrize('path', ['/http/anything', '/http/', '/http/anything/deeper'])
def test_http_descendants_require_bearer(remote_db, path):
    with TestClient(mcp_server.create_http_app()) as client:
        response = client.post(path, json={'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {'protocolVersion': '2024-11-05', 'capabilities': {}, 'clientInfo': {'name': 'test', 'version': '1'}}})
        assert response.status_code == 401


@pytest.mark.parametrize('path', ['/messages/child', '/messages/child/grandchild'])
def test_sse_descendants_keep_session_protection(remote_db, path):
    from uuid import UUID
    from starlette.responses import JSONResponse
    _, users, tokens = remote_db
    async def endpoint(scope, receive, send):
        await JSONResponse({'ok': True})(scope, receive, send)
    wrapped = mcp_server.MCPTokenAuthMiddleware(endpoint)
    session_id = UUID('12345678-1234-5678-abcd-123456789abc')
    wrapped.session_users[session_id.hex] = users[0].id
    client = TestClient(wrapped)
    assert client.post(f'{path}?session_id={session_id}').status_code == 401
    assert client.post(f'{path}?session_id={session_id}', headers=headers(tokens[1])).status_code == 403
    client.close()


def test_mcp_completion_returns_actual_cultivation_settlement(remote_db):
    import json
    db, users, tokens = remote_db
    mcp_server.login_with_token(tokens[0])
    task = mcp_server.create_task('Reward result')
    completed = mcp_server.complete_task(task['id'])
    assert completed['cultivation_reward']['cultivation'] > 0
    assert completed['cultivation_reward']['log_id']
    assert json.dumps(completed)
    habit = mcp_server.create_habit('China habit')
    result = mcp_server.complete_habit(habit['id'])
    assert result['completed_today'] is True
    assert result['cultivation_reward']['cultivation'] > 0


def test_mcp_finance_results_and_public_user_are_json_safe(remote_db):
    db, users, tokens = remote_db
    mcp_server.login_with_token(tokens[0])
    account = mcp_server.create_account('Decimal account', balance=12.34)
    assert json.dumps(account)
    assert 'password_hash' not in mcp_server._serialize(users[0])


def test_existing_task_tools_support_schedule_and_occurrence(remote_db):
    from app.timezone import today
    db, users, tokens = remote_db
    mcp_server.login_with_token(tokens[0])
    day = today().isoformat()
    task = mcp_server.create_task('Recurring task', schedule={'rule_type': 'daily', 'starts_on': day})
    assert task['schedule']['rule_type'] == 'daily'
    result = mcp_server.complete_task(task['id'], occurrence_date=day)
    assert result['occurrence_status'] == 'completed'
    balance = mcp_server.get_profile()['coins']
    mcp_server.complete_task(task['id'], occurrence_date=day)
    assert mcp_server.get_profile()['coins'] == balance
    updated = mcp_server.update_task(task['id'], schedule={'rule_type': 'weekly', 'weekdays': [0], 'starts_on': day})
    assert updated['schedule']['rule_type'] == 'weekly'
    assert mcp_server.update_task(task['id'], clear_schedule=True)['schedule'] is None


def test_existing_task_tools_can_clear_dates(remote_db):
    _, _, tokens = remote_db
    mcp_server.login_with_token(tokens[0])
    task = mcp_server.create_task('Clear date', deadline='2027-01-01', start_date='2026-12-01')
    updated = mcp_server.update_task(task['id'], clear_deadline=True, clear_start_date=True)
    assert updated['deadline'] is None and updated['start_date'] is None
    with pytest.raises(ValueError):
        mcp_server.update_task(task['id'], deadline='2027-01-01', clear_deadline=True)


def test_note_updates_can_use_revision_conflict_protection(remote_db):
    from app.services.note import NoteRevisionConflict
    _, _, tokens = remote_db
    mcp_server.login_with_token(tokens[0])
    notebook = mcp_server.create_notebook('Revision test')
    note = mcp_server.create_note(notebook['id'], 'Safe edit', 'first')
    revision = mcp_server.get_note(note['id'])['content_revision']
    updated = mcp_server.update_note(note['id'], content='second', base_revision=revision)
    assert updated['content_revision'] == revision + 1
    with pytest.raises(NoteRevisionConflict):
        mcp_server.update_note(note['id'], content='stale edit', base_revision=revision)
    assert mcp_server.get_note(note['id'])['content'] == 'second'
