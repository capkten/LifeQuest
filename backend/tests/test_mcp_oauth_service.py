import base64
import hashlib
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit
import pytest
from app.models.user import User
from app.services.mcp_oauth import MCPOAuthService, OAuthError

VERIFIER = "a" * 64
RESOURCE = "https://life.example/mcp/http"
CALLBACK = "https://chat.example/callback"

@pytest.fixture
def service(database, monkeypatch):
    config = SimpleNamespace(enabled=True, issuer_url="https://life.example", resource_url=RESOURCE, frontend_url="https://life.example", access_seconds=900, refresh_seconds=2592000, request_seconds=600, code_seconds=120, allow_loopback=False)
    monkeypatch.setattr("app.oauth_config.get_oauth_config", lambda: config)
    users = [User(username=n, email=n+"@example.com", password_hash="unused") for n in ("owner", "other")]
    database.add_all(users)
    database.commit()
    return MCPOAuthService(database), *users

def register(s, **kw):
    return s.register_client({"client_name":"Chat", "redirect_uris":[CALLBACK], "token_endpoint_auth_method":"none", **kw})

def code(s, u, c, **kw):
    request = s.begin_authorization({"client_id":c["client_id"], "redirect_uri":CALLBACK, "response_type":"code", "scope":"mcp", "resource":RESOURCE, "state":"state", "code_challenge_method":"S256", "code_challenge":base64.urlsafe_b64encode(hashlib.sha256(VERIFIER.encode()).digest()).rstrip(b"=").decode(), **kw})
    s.authorization_details(request,u.id)
    callback = s.consent(request,u.id,True)
    if "?" in kw.get("redirect_uri", ""):
        assert callback.startswith(kw["redirect_uri"] + "&")
    result = parse_qs(urlsplit(callback).query)
    assert result["state"] == ["state"]
    return result["code"][0]

def exchange(s,c,value,**kw):
    return s.exchange_token({"grant_type":"authorization_code", "client_id":c["client_id"], "code":value, "redirect_uri":CALLBACK, "resource":RESOURCE, "code_verifier":VERIFIER, **kw})

def test_lifecycle_hashes_and_replay(service):
    s,u,_=service
    c=register(s); value=code(s,u,c); tokens=exchange(s,c,value)
    assert s.authenticate_access_token(tokens["access_token"]) == u.id
    assert s.authenticate_access_token(tokens["refresh_token"]) is None
    from app.models.mcp_oauth import MCPOAuthCode, MCPOAuthToken
    assert s.db.query(MCPOAuthCode).one().code_hash != value
    pair=s.db.query(MCPOAuthToken).one()
    assert pair.access_hash != tokens["access_token"] and pair.refresh_hash != tokens["refresh_token"]
    with pytest.raises(OAuthError): exchange(s,c,value)

def test_refresh_replay_revokes_family(service):
    s,u,_=service;c=register(s); first=exchange(s,c,code(s,u,c))
    form={"grant_type":"refresh_token","client_id":c["client_id"],"refresh_token":first["refresh_token"]}
    second=s.exchange_token(form)
    assert second["refresh_token"]!=first["refresh_token"]
    with pytest.raises(OAuthError):s.exchange_token(form)
    assert s.authenticate_access_token(second["access_token"]) is None

@pytest.mark.parametrize("kw",[{"redirect_uri":"https://evil.example"},{"scope":"admin"},{"resource":"https://evil.example"},{"code_challenge_method":"plain"},{"code_challenge":"short"}])
def test_bad_authorization(service,kw):
    s,u,_=service
    with pytest.raises(OAuthError):code(s,u,register(s),**kw)

@pytest.mark.parametrize("uri",["http://remote.example/cb","https://a.example/#frag","https://user:pass@a.example/cb","https://*.example/cb"])
def test_bad_redirect(service,uri):
    with pytest.raises(OAuthError):register(service[0],redirect_uris=[uri])

def test_owner_revocation(service):
    s,u,other=service;c=register(s);tokens=exchange(s,c,code(s,u,c));grant=s.list_grants(u.id)[0]
    assert s.list_grants(other.id)==[] and "hash" not in str(grant)
    with pytest.raises(OAuthError):s.revoke_grant(grant["id"],other.id)
    s.revoke_grant(grant["id"],u.id)
    assert s.authenticate_access_token(tokens["access_token"]) is None

def test_pkce_client_isolation(service):
    s,u,_=service;c=register(s);other=register(s);value=code(s,u,c)
    with pytest.raises(OAuthError):exchange(s,other,value)
    with pytest.raises(OAuthError):exchange(s,c,value,code_verifier="b"*64)
    assert exchange(s,c,value)["access_token"]

@pytest.mark.parametrize("method",["client_secret_post","client_secret_basic"])
def test_client_auth(service,method):
    s,u,_=service;c=register(s,token_endpoint_auth_method=method);value=code(s,u,c)
    with pytest.raises(OAuthError):exchange(s,c,value)
    form={"grant_type":"authorization_code","client_id":c["client_id"],"code":value,"resource":RESOURCE,"redirect_uri":CALLBACK,"code_verifier":VERIFIER}
    auth=None
    if method=="client_secret_post":form["client_secret"]=c["client_secret"]
    else:
        auth="Basic "+base64.b64encode(f'{c["client_id"]}:{c["client_secret"]}'.encode()).decode();form.pop("client_id")
    assert s.exchange_token(form,auth)["access_token"]

def test_consent_first_user_binding_and_denial(service):
    s,u,other=service;c=register(s)
    request=s.begin_authorization({"client_id":c["client_id"],"redirect_uri":CALLBACK,"response_type":"code","scope":"mcp","resource":RESOURCE,"state":"<& state>","code_challenge_method":"S256","code_challenge":base64.urlsafe_b64encode(hashlib.sha256(VERIFIER.encode()).digest()).rstrip(b"=").decode()})
    with pytest.raises(OAuthError):s.consent(request,u.id,True)
    assert s.authorization_details(request,u.id)["user_id"]==str(u.id)
    with pytest.raises(OAuthError):s.authorization_details(request,other.id)
    with pytest.raises(OAuthError):s.consent(request,other.id,True)
    query=parse_qs(urlsplit(s.consent(request,u.id,False)).query)
    assert query=={"error":["access_denied"],"state":["<& state>"]}
    with pytest.raises(OAuthError):s.consent(request,u.id,True)
    assert s.list_grants(u.id)==[]


def test_access_and_code_expiry(service):
    from datetime import timedelta
    from app.models.mcp_oauth import MCPOAuthCode, MCPOAuthToken, now
    s,u,_=service;c=register(s);value=code(s,u,c)
    row=s.db.query(MCPOAuthCode).one();row.expires_at=now()-timedelta(seconds=1);s.db.commit()
    with pytest.raises(OAuthError):exchange(s,c,value)
    tokens=exchange(s,c,code(s,u,c))
    pair=s.db.query(MCPOAuthToken).one();pair.access_expires_at=now()-timedelta(seconds=1);s.db.commit()
    assert s.authenticate_access_token(tokens["access_token"]) is None
    assert s.exchange_token({"grant_type":"refresh_token","client_id":c["client_id"],"refresh_token":tokens["refresh_token"]})["access_token"]


def test_token_resource_scope_and_cross_client_revoke(service):
    s,u,_=service;c=register(s);other=register(s);value=code(s,u,c)
    with pytest.raises(OAuthError):exchange(s,c,value,resource="https://evil.example")
    tokens=exchange(s,c,value)
    s.revoke_token({"client_id":other["client_id"],"token":tokens["access_token"]})
    assert s.authenticate_access_token(tokens["access_token"])==u.id
    form={"grant_type":"refresh_token","client_id":c["client_id"],"refresh_token":tokens["refresh_token"]}
    for kw in ({"resource":"https://evil.example"},{"scope":"admin"},{"client_id":other["client_id"]}):
        with pytest.raises(OAuthError):s.exchange_token({**form,**kw})
    s.revoke_token({"client_id":c["client_id"],"token":tokens["refresh_token"]})
    assert s.authenticate_access_token(tokens["access_token"]) is None
    with pytest.raises(OAuthError):s.exchange_token(form)


def test_disabled_and_no_foreign_bearer_acceptance(service):
    s,_,_=service
    assert s.authenticate_access_token("eyJhbGciOiJIUzI1NiJ9.fake.jwt") is None
    assert s.authenticate_access_token("lq_mcp_personal-token") is None
    s.config.enabled=False
    with pytest.raises(OAuthError):register(s)

def test_code_replay_revokes_issued_tokens(service):
    s,u,_=service;c=register(s);value=code(s,u,c);tokens=exchange(s,c,value)
    with pytest.raises(OAuthError):exchange(s,c,value)
    assert s.authenticate_access_token(tokens["access_token"]) is None

@pytest.mark.parametrize("metadata", [
    {"grant_types": ["authorization_code"]},
    {"grant_types": ["refresh_token"]},
    {"grant_types": ["authorization_code", "refresh_token", "refresh_token"]},
    {"scope": "admin"},
    {"scope": "mcp admin"},
])
def test_registration_rejects_silent_capability_expansion(service, metadata):
    with pytest.raises(OAuthError) as caught:
        register(service[0], **metadata)
    assert caught.value.error == "invalid_client_metadata"


def test_registration_supported_grants_accepts_either_order(service):
    client = register(service[0], grant_types=["refresh_token", "authorization_code"], scope="mcp")
    assert set(client["grant_types"]) == {"authorization_code", "refresh_token"}
    assert client["scope"] == "mcp"

@pytest.mark.parametrize("key", ["code", "state", "error", "error_description"])
def test_registration_rejects_reserved_callback_response_keys(service, key):
    with pytest.raises(OAuthError) as caught:
        register(service[0], redirect_uris=[CALLBACK + "?" + key + "=fixed"])
    assert caught.value.error == "invalid_redirect_uri"


def test_fixed_callback_query_preserved_and_old_resource_request_rejected(service):
    s,u,_=service
    callback = CALLBACK + "?tenant=life%20quest&empty="
    c=register(s, redirect_uris=[callback])
    value=code(s,u,c,redirect_uri=callback)
    assert exchange(s,c,value,redirect_uri=callback)["access_token"]
    request=s.begin_authorization({"client_id":c["client_id"],"redirect_uri":callback,"response_type":"code","scope":"mcp","resource":RESOURCE,"code_challenge_method":"S256","code_challenge":base64.urlsafe_b64encode(hashlib.sha256(VERIFIER.encode()).digest()).rstrip(b"=").decode()})
    s.authorization_details(request,u.id)
    s.config.resource_url="https://new.example/mcp/http"
    with pytest.raises(OAuthError):s.authorization_details(request,u.id)
    with pytest.raises(OAuthError):s.consent(request,u.id,True)
