"""Real legacy transport compatibility using disposable databases and processes."""
import asyncio
import os
from pathlib import Path
import socket
import sys
import threading
import time
from uuid import uuid4

import httpx
import pytest
from mcp import ClientSession
from mcp.client.sse import sse_client
from mcp.client.stdio import StdioServerParameters, stdio_client
from sqlalchemy.orm import sessionmaker
import uvicorn

from app.models.user import User
from app.schemas.mcp_access_token import MCPAccessTokenCreate
from app.services.mcp_access_token import MCPAccessTokenService
import mcp_server


@pytest.fixture
def transport_users(database):
    users = [User(username=f'transport-{uuid4().hex}', email=f'{uuid4().hex}@example.com', password_hash='unused') for _ in range(2)]
    database.add_all(users)
    database.commit()
    credentials = [MCPAccessTokenService(database).create_token(user.id, MCPAccessTokenCreate(name='transport')) for user in users]
    return database, users, credentials


def _payload(result):
    import json
    assert result.isError is False, result
    return json.loads(result.content[0].text)


async def _check_session(session, user, token, other_token):
    await session.initialize()
    registered = {tool.name for tool in (await session.list_tools()).tools}
    assert {'get_profile', 'list_tasks', 'purchase_shop_item', 'get_cultivation_overview'} <= registered
    assert _payload(await session.call_tool('get_profile', {}))['id'] == str(user.id)
    rejected = await session.call_tool('login_with_token', {'token': other_token})
    assert rejected.isError
    assert _payload(await session.call_tool('get_profile', {}))['id'] == str(user.id)


def test_real_stdio_subprocess_revalidates_token(transport_users, tmp_path):
    database, users, credentials = transport_users
    # Explicitly override all credential/database choices inherited from the host.
    environment = dict(os.environ)
    environment.update(DATABASE_URL=str(database.bind.url), SECRET_KEY='isolated-transport-test', MCP_AUTOSTART='false', LIFEQUEST_MCP_TOKEN=credentials[0][1], PYTHONPATH=str(Path(mcp_server.__file__).parent))
    environment.pop('LIFEQUEST_USER_ID', None)
    environment.pop('LIFEQUEST_MCP_USER_ID', None)
    parameters = StdioServerParameters(command=sys.executable, args=[str(Path(mcp_server.__file__).resolve()), '--transport', 'stdio'], env=environment, cwd=str(tmp_path))

    async def exercise():
        async with asyncio.timeout(30):
            with (tmp_path / 'stdio-stderr.log').open('w', encoding='utf-8') as errors:
                async with stdio_client(parameters, errlog=errors) as streams:
                    async with ClientSession(*streams) as session:
                        await _check_session(session, users[0], credentials[0][1], credentials[1][1])
                        MCPAccessTokenService(database).revoke(credentials[0][0].id, users[0].id)
                        assert (await session.call_tool('get_profile', {})).isError
    asyncio.run(exercise())


@pytest.fixture
def socket_mcp(transport_users, monkeypatch):
    database, users, credentials = transport_users
    monkeypatch.setattr(mcp_server, 'SessionLocal', sessionmaker(bind=database.bind, autocommit=False, autoflush=False))
    monkeypatch.setattr(mcp_server, '_db_initialized', True)
    monkeypatch.delenv('LIFEQUEST_MCP_TOKEN', raising=False)
    monkeypatch.delenv('LIFEQUEST_USER_ID', raising=False)
    monkeypatch.delenv('LIFEQUEST_MCP_USER_ID', raising=False)
    listener = socket.socket()
    listener.bind(('127.0.0.1', 0))
    listener.listen(128)
    address = f'http://127.0.0.1:{listener.getsockname()[1]}'
    server = uvicorn.Server(uvicorn.Config(mcp_server.create_http_app(), log_level='error', lifespan='on'))
    thread = threading.Thread(target=server.run, kwargs={'sockets': [listener]}, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 10
        while not server.started and thread.is_alive() and time.monotonic() < deadline:
            time.sleep(0.01)
        assert server.started, 'MCP socket server failed to start'
        yield address
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        if thread.is_alive():
            server.force_exit = True
            thread.join(timeout=2)
        listener.close()
        assert not thread.is_alive(), 'MCP socket server did not stop'


def test_real_sse_bearer_compatibility(socket_mcp, transport_users):
    database, users, credentials = transport_users

    async def exercise():
        async with asyncio.timeout(20):
            async with sse_client(socket_mcp + '/sse', headers={'Authorization': f'Bearer {credentials[0][1]}'}) as streams:
                async with ClientSession(*streams) as session:
                    await _check_session(session, users[0], credentials[0][1], credentials[1][1])
    asyncio.run(exercise())
    MCPAccessTokenService(database).revoke(credentials[0][0].id, users[0].id)
    response = httpx.get(socket_mcp + '/sse', headers={'Authorization': f'Bearer {credentials[0][1]}'}, timeout=5)
    assert response.status_code == 401


def test_real_sse_login_session_revocation(socket_mcp, transport_users):
    database, users, credentials = transport_users

    async def exercise():
        async with asyncio.timeout(20):
            async with sse_client(socket_mcp + '/sse') as streams:
                async with ClientSession(*streams) as session:
                    await session.initialize()
                    assert (await session.call_tool('get_profile', {})).isError
                    login = await session.call_tool('login_with_token', {'token': credentials[0][1]})
                    assert not login.isError
                    assert _payload(await session.call_tool('get_profile', {}))['id'] == str(users[0].id)
                    assert (await session.call_tool('login_with_token', {'token': credentials[1][1]})).isError
                    MCPAccessTokenService(database).revoke(credentials[0][0].id, users[0].id)
                    assert (await session.call_tool('get_profile', {})).isError
    asyncio.run(exercise())
