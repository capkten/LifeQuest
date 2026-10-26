"""Competing requests use independent sessions against isolated SQLite."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from sqlalchemy.orm import sessionmaker

from app.models.mcp_oauth import MCPOAuthCode, MCPOAuthGrant, MCPOAuthToken
from app.services.mcp_oauth import MCPOAuthService, OAuthError
from tests.test_mcp_oauth_service import service, register, code, exchange, RESOURCE, VERIFIER, CALLBACK


def race(service, invoke):
    factory = sessionmaker(bind=service.db.get_bind())
    barrier = Barrier(2)
    def worker(_):
        with factory() as db:
            instance = MCPOAuthService(db)
            barrier.wait(timeout=5)
            try:
                return invoke(instance)
            except OAuthError as error:
                return error.error
    with ThreadPoolExecutor(max_workers=2) as executor:
        return list(executor.map(worker, range(2)))


def test_concurrent_code_exchange_never_issues_two_token_pairs(service):
    s, owner, _ = service
    client = register(s)
    value = code(s, owner, client)
    results = race(s, lambda other: exchange(other, client, value))
    assert sum(isinstance(result, dict) for result in results) == 1
    assert results.count('invalid_grant') == 1
    s.db.expire_all()
    assert s.db.query(MCPOAuthToken).count() == 1
    assert s.db.query(MCPOAuthGrant).one().revoked_at is not None
    winner = next(result for result in results if isinstance(result, dict))
    assert s.authenticate_access_token(winner['access_token']) is None


def test_concurrent_refresh_replay_revokes_winner_and_never_duplicates(service):
    s, owner, _ = service
    client = register(s)
    first = exchange(s, client, code(s, owner, client))
    form = {'grant_type': 'refresh_token', 'client_id': client['client_id'], 'refresh_token': first['refresh_token']}
    results = race(s, lambda other: other.exchange_token(form))
    assert sum(isinstance(result, dict) for result in results) == 1
    assert results.count('invalid_grant') == 1
    s.db.expire_all()
    assert s.db.query(MCPOAuthToken).count() == 2
    assert s.db.query(MCPOAuthGrant).one().revoked_at is not None
    winner = next(result for result in results if isinstance(result, dict))
    assert s.authenticate_access_token(winner['access_token']) is None
