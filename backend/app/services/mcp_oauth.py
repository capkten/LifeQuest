"""OAuth authorization-code flow dedicated to the MCP protected resource."""
import base64
import hashlib
import hmac
import re
import secrets
from datetime import timedelta
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit, unquote_plus
from uuid import UUID
from sqlalchemy import update
from app.models.user import User
from app.models.mcp_oauth import MCPOAuthClient, MCPOAuthRequest, MCPOAuthGrant, MCPOAuthCode, MCPOAuthToken, now


class OAuthError(Exception):
    def __init__(self, error, error_description, status_code=400):
        super().__init__(error_description)
        self.error = error
        self.error_description = error_description
        self.status_code = status_code


def digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def fail(error="invalid_request", description="Invalid OAuth request", status=400):
    raise OAuthError(error, description, status)


class MCPOAuthService:
    def __init__(self, db):
        from app.oauth_config import get_oauth_config
        self.db = db
        self.config = get_oauth_config()

    def _enabled(self):
        if not self.config.enabled:
            fail("temporarily_unavailable", "MCP OAuth is disabled", 503)

    def _redirect(self, uri):
        if not isinstance(uri, str) or len(uri) > 2048 or any(ord(c) < 33 for c in uri):
            fail("invalid_redirect_uri", "Invalid redirect URI")
        try:
            parsed = urlsplit(uri)
            port = parsed.port
        except ValueError:
            fail("invalid_redirect_uri", "Invalid redirect URI")
        allowed_http = self.config.allow_loopback and parsed.hostname in ("127.0.0.1", "::1", "localhost")
        if (not parsed.hostname or parsed.username is not None or parsed.password is not None
                or parsed.fragment or "#" in uri or "*" in uri or "\\" in uri
                or parsed.scheme != "https" and not (parsed.scheme == "http" and allowed_http)):
            fail("invalid_redirect_uri", "Redirect URI must use HTTPS with no fragment or credentials")
        return uri

    def register_client(self, payload):
        self._enabled()
        uris = payload.get("redirect_uris")
        if not isinstance(uris, list) or not 1 <= len(uris) <= 20:
            fail("invalid_client_metadata", "Provide one to twenty redirect URIs")
        uris = list(dict.fromkeys(self._redirect(uri) for uri in uris))
        method = payload.get("token_endpoint_auth_method", "none")
        if method not in ("none", "client_secret_post", "client_secret_basic"):
            fail("invalid_client_metadata", "Unsupported client authentication method")
        grants = payload.get("grant_types", ["authorization_code", "refresh_token"])
        if (not isinstance(grants, list) or len(grants) != 2
                or any(not isinstance(value, str) for value in grants)
                or set(grants) != {"authorization_code", "refresh_token"}):
            fail("invalid_client_metadata", "Register both authorization_code and refresh_token grants")
        if payload.get("scope", "mcp") != "mcp":
            fail("invalid_client_metadata", "Only mcp scope is supported")
        if payload.get("response_types", ["code"]) != ["code"]:
            fail("invalid_client_metadata", "Only code response type is supported")
        name = payload.get("client_name", "MCP client")
        if not isinstance(name, str) or not 1 <= len(name) <= 200:
            fail("invalid_client_metadata", "Invalid client name")
        secret = secrets.token_urlsafe(48) if method != "none" else None
        row = MCPOAuthClient(id="lq_client_" + secrets.token_urlsafe(24), name=name,
            redirect_uris=uris, auth_method=method, secret_hash=digest(secret) if secret else None)
        self.db.add(row)
        self.db.commit()
        result = {"client_id": row.id, "client_name": row.name, "redirect_uris": uris,
            "token_endpoint_auth_method": method, "grant_types": ["authorization_code", "refresh_token"], "response_types": ["code"], "scope": "mcp"}
        if secret:
            result.update(client_secret=secret, client_secret_expires_at=0)
        return result

    def _client(self, client_id):
        client = self.db.get(MCPOAuthClient, client_id) if isinstance(client_id, str) else None
        if not client:
            fail("invalid_client", "Unknown OAuth client", 401)
        return client

    def begin_authorization(self, params):
        self._enabled()
        client = self._client(params.get("client_id"))
        redirect = params.get("redirect_uri")
        if redirect not in client.redirect_uris:
            fail("invalid_request", "Redirect URI is not registered")
        if params.get("response_type") != "code":
            fail("unsupported_response_type", "Only authorization code is supported")
        if params.get("scope") != "mcp":
            fail("invalid_scope", "Only mcp scope is supported")
        if params.get("resource") != self.config.resource_url:
            fail("invalid_target", "Resource does not match MCP resource")
        challenge = params.get("code_challenge", "")
        if params.get("code_challenge_method") != "S256" or not isinstance(challenge, str) or not re.fullmatch(r"[A-Za-z0-9_-]{43}", challenge):
            fail("invalid_request", "PKCE S256 is required")
        state = params.get("state")
        if state is not None and (not isinstance(state, str) or len(state) > 4096):
            fail("invalid_request", "Invalid state")
        handle = secrets.token_urlsafe(48)
        self.db.add(MCPOAuthRequest(request_hash=digest(handle), client_id=client.id, redirect_uri=redirect,
            state=state, challenge=challenge, scope="mcp", resource=self.config.resource_url,
            expires_at=now() + timedelta(seconds=self.config.request_seconds)))
        self.db.commit()
        return handle

    def _request(self, request_id, user_id, bind=False):
        self._enabled()
        if not isinstance(request_id, str) or len(request_id) > 200:
            fail("invalid_request", "Invalid authorization request")
        row = self.db.get(MCPOAuthRequest, digest(request_id), populate_existing=True)
        if not row or row.consumed_at or row.expires_at <= now():
            fail("invalid_request", "Authorization request expired or consumed")
        if not self.db.get(User, user_id):
            fail("access_denied", "Unknown user", 403)
        if bind and row.user_id is None:
            self.db.execute(update(MCPOAuthRequest).where(MCPOAuthRequest.request_hash == row.request_hash,
                MCPOAuthRequest.user_id.is_(None), MCPOAuthRequest.consumed_at.is_(None)).values(user_id=user_id),
                execution_options={"synchronize_session": False})
            self.db.commit()
            self.db.refresh(row)
        if row.user_id != user_id:
            fail("access_denied", "Authorization request belongs to another user", 403)
        return row

    def authorization_details(self, request_id, user_id):
        row = self._request(request_id, user_id, bind=True)
        return {"client_name": self._client(row.client_id).name, "redirect_uri": row.redirect_uri,
            "scope": row.scope, "resource": row.resource, "user_id": str(row.user_id)}

    def consent(self, request_id, user_id, approve):
        row = self._request(request_id, user_id)
        consumed = self.db.execute(update(MCPOAuthRequest).where(MCPOAuthRequest.request_hash == row.request_hash,
            MCPOAuthRequest.consumed_at.is_(None), MCPOAuthRequest.expires_at > now()).values(consumed_at=now()),
            execution_options={"synchronize_session": False}).rowcount
        if not consumed:
            self.db.rollback()
            fail("invalid_request", "Authorization request already consumed")
        query = list(parse_qsl(urlsplit(row.redirect_uri).query, keep_blank_values=True))
        if row.state is not None:
            query.append(("state", row.state))
        if approve:
            grant = MCPOAuthGrant(client_id=row.client_id, user_id=user_id, scope=row.scope, resource=row.resource)
            self.db.add(grant)
            self.db.flush()
            code = secrets.token_urlsafe(48)
            self.db.add(MCPOAuthCode(code_hash=digest(code), grant_id=grant.id, redirect_uri=row.redirect_uri,
                challenge=row.challenge, expires_at=now() + timedelta(seconds=self.config.code_seconds)))
            query.append(("code", code))
        else:
            query.append(("error", "access_denied"))
        self.db.commit()
        parsed = urlsplit(row.redirect_uri)
        return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(query), ""))

    def _authenticate_client(self, form, authorization):
        client_id, secret, method = form.get("client_id"), form.get("client_secret"), "client_secret_post" if "client_secret" in form else "none"
        if authorization:
            if not authorization.startswith("Basic ") or "client_secret" in form:
                fail("invalid_client", "Invalid client authentication", 401)
            try:
                decoded = base64.b64decode(authorization[6:], validate=True).decode("utf-8")
                basic_id, secret = (unquote_plus(v) for v in decoded.split(":", 1))
            except (ValueError, UnicodeError):
                fail("invalid_client", "Invalid Basic client authentication", 401)
            if client_id is not None and client_id != basic_id:
                fail("invalid_client", "Conflicting client credentials", 401)
            client_id, method = basic_id, "client_secret_basic"
        client = self._client(client_id)
        if method != client.auth_method or method != "none" and (not isinstance(secret, str) or not hmac.compare_digest(digest(secret), client.secret_hash)):
            fail("invalid_client", "Invalid client credentials", 401)
        return client

    def _grant(self, grant_id):
        row = self.db.get(MCPOAuthGrant, grant_id, populate_existing=True)
        if not row or row.revoked_at or row.resource != self.config.resource_url or row.scope != "mcp" or not self.db.get(User, row.user_id):
            fail("invalid_grant", "Authorization is no longer valid")
        return row

    def _tokens(self, grant):
        access, refresh = "lq_oa_" + secrets.token_urlsafe(48), "lq_or_" + secrets.token_urlsafe(48)
        self.db.add(MCPOAuthToken(grant_id=grant.id, access_hash=digest(access), refresh_hash=digest(refresh),
            access_expires_at=now()+timedelta(seconds=self.config.access_seconds),
            refresh_expires_at=now()+timedelta(seconds=self.config.refresh_seconds)))
        self.db.commit()
        return {"access_token": access, "refresh_token": refresh, "token_type": "Bearer",
            "expires_in": self.config.access_seconds, "scope": grant.scope}

    def exchange_token(self, form, authorization=None):
        self._enabled()
        client = self._authenticate_client(form, authorization)
        kind = form.get("grant_type")
        if kind == "authorization_code":
            if form.get("resource") != self.config.resource_url:
                fail("invalid_target", "MCP resource is required")
            raw = form.get("code", "")
            row = self.db.get(MCPOAuthCode, digest(raw)) if isinstance(raw, str) else None
            if not row or row.expires_at <= now():
                fail("invalid_grant", "Invalid or expired authorization code")
            grant = self._grant(row.grant_id)
            verifier = form.get("code_verifier", "")
            if grant.client_id != client.id or row.redirect_uri != form.get("redirect_uri"):
                fail("invalid_grant", "Code client or redirect mismatch")
            if not isinstance(verifier, str) or not re.fullmatch(r"[A-Za-z0-9._~-]{43,128}", verifier):
                fail("invalid_grant", "Invalid PKCE verifier")
            challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
            if not hmac.compare_digest(challenge, row.challenge):
                fail("invalid_grant", "PKCE verification failed")
            if row.consumed_at:
                self.db.execute(update(MCPOAuthGrant).where(MCPOAuthGrant.id == grant.id).values(revoked_at=now()))
                self.db.commit()
                fail("invalid_grant", "Authorization code replayed")
            count = self.db.execute(update(MCPOAuthCode).where(MCPOAuthCode.code_hash == row.code_hash,
                MCPOAuthCode.consumed_at.is_(None), MCPOAuthCode.expires_at > now()).values(consumed_at=now()),
                execution_options={"synchronize_session": False}).rowcount
            if not count:
                self.db.execute(update(MCPOAuthGrant).where(MCPOAuthGrant.id == grant.id).values(revoked_at=now()))
                self.db.commit()
                fail("invalid_grant", "Authorization code already consumed")
        elif kind == "refresh_token":
            if form.get("resource", self.config.resource_url) != self.config.resource_url:
                fail("invalid_target", "Resource mismatch")
            if form.get("scope", "mcp") != "mcp":
                fail("invalid_scope", "Scope cannot change")
            raw = form.get("refresh_token", "")
            row = self.db.query(MCPOAuthToken).filter_by(refresh_hash=digest(raw)).first() if isinstance(raw, str) else None
            if not row:
                fail("invalid_grant", "Invalid refresh token")
            grant = self._grant(row.grant_id)
            if grant.client_id != client.id:
                fail("invalid_grant", "Refresh token client mismatch")
            count = self.db.execute(update(MCPOAuthToken).where(MCPOAuthToken.id == row.id,
                MCPOAuthToken.refresh_consumed_at.is_(None), MCPOAuthToken.refresh_expires_at > now()).values(refresh_consumed_at=now()),
                execution_options={"synchronize_session": False}).rowcount
            if not count:
                self.db.refresh(row)
                if row.refresh_consumed_at:
                    self.db.execute(update(MCPOAuthGrant).where(MCPOAuthGrant.id == grant.id).values(revoked_at=now()))
                    self.db.commit()  # Persist replay revocation even though the route returns an error.
                else:
                    self.db.rollback()
                fail("invalid_grant", "Refresh token expired or replayed")
        else:
            fail("unsupported_grant_type", "Unsupported grant type")
        return self._tokens(grant)

    def authenticate_access_token(self, raw_token):
        if not self.config.enabled or not isinstance(raw_token, str) or not raw_token.startswith("lq_oa_"):
            return None
        pair = self.db.query(MCPOAuthToken).filter_by(access_hash=digest(raw_token)).populate_existing().first()
        if not pair or pair.access_expires_at <= now():
            return None
        try:
            return self._grant(pair.grant_id).user_id
        except OAuthError:
            return None

    def revoke_token(self, form, authorization=None):
        self._enabled()
        client = self._authenticate_client(form, authorization)
        raw = form.get("token", "")
        if not isinstance(raw, str):
            return
        hashed = digest(raw)
        pair = self.db.query(MCPOAuthToken).filter((MCPOAuthToken.access_hash == hashed) | (MCPOAuthToken.refresh_hash == hashed)).first()
        if pair:
            self.db.execute(update(MCPOAuthGrant).where(MCPOAuthGrant.id == pair.grant_id,
                MCPOAuthGrant.client_id == client.id).values(revoked_at=now()))
            self.db.commit()

    def list_grants(self, user_id):
        self._enabled()
        rows = self.db.query(MCPOAuthGrant).filter_by(user_id=user_id, revoked_at=None).all()
        return [{"id": str(row.id), "client_name": self._client(row.client_id).name,
            "scope": row.scope, "resource": row.resource, "created_at": row.created_at.isoformat()} for row in rows]

    def revoke_grant(self, grant_id, user_id):
        self._enabled()
        try:
            grant_id = UUID(str(grant_id))
        except (ValueError, TypeError):
            fail("invalid_request", "Unknown authorization", 404)
        count = self.db.execute(update(MCPOAuthGrant).where(MCPOAuthGrant.id == grant_id,
            MCPOAuthGrant.user_id == user_id).values(revoked_at=now())).rowcount
        if not count:
            self.db.rollback()
            fail("invalid_request", "Unknown authorization", 404)
        self.db.commit()
