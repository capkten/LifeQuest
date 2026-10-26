"""OAuth protocol endpoints and authenticated browser consent."""
import json
from collections import defaultdict, deque
from time import monotonic
from urllib.parse import urlencode, urlsplit, urlunsplit

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, ConfigDict, StrictBool
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.database import get_db
from app.oauth_config import get_oauth_config, authorization_server_metadata, protected_resource_metadata
from app.services.mcp_oauth import MCPOAuthService, OAuthError

router = APIRouter(tags=['MCP OAuth'])
_NO_STORE = {'Cache-Control': 'no-store', 'Pragma': 'no-cache', 'Referrer-Policy': 'no-referrer'}
_registration_windows = defaultdict(deque)


def _enabled():
    config = get_oauth_config()
    if not config.enabled:
        raise HTTPException(404, 'OAuth is not enabled')
    return config


def _invoke(db, method, *args, **kwargs):
    try:
        return getattr(MCPOAuthService(db), method)(*args, **kwargs)
    except OAuthError as exc:
        headers = dict(_NO_STORE)
        if exc.status_code == 401:
            headers['WWW-Authenticate'] = 'Basic realm="LifeQuest OAuth"'
        return JSONResponse({'error': exc.error, 'error_description': exc.error_description}, status_code=exc.status_code, headers=headers)


async def _body(request, *, form=False):
    chunks = bytearray()
    async for chunk in request.stream():
        chunks.extend(chunk)
        if len(chunks) > 16384:
            raise OAuthError('invalid_request', 'Request body is too large')
    if form:
        if request.headers.get('content-type', '').split(';')[0].strip() != 'application/x-www-form-urlencoded':
            raise OAuthError('invalid_request', 'Use application/x-www-form-urlencoded')
        from urllib.parse import parse_qsl
        try:
            entries = parse_qsl(chunks.decode('utf-8'), keep_blank_values=True, max_num_fields=30)
        except (ValueError, UnicodeError):
            raise OAuthError('invalid_request', 'Invalid form body')
        result = dict(entries)
        if len(result) != len(entries):
            raise OAuthError('invalid_request', 'Duplicate parameters are not allowed')
        return result
    try:
        data = json.loads(chunks)
    except (ValueError, UnicodeError):
        raise OAuthError('invalid_request', 'Invalid JSON body')
    if not isinstance(data, dict):
        raise OAuthError('invalid_request', 'Expected a JSON object')
    return data


def _error(exc):
    headers = dict(_NO_STORE)
    if exc.status_code == 401:
        headers['WWW-Authenticate'] = 'Basic realm="LifeQuest OAuth"'
    return JSONResponse({'error': exc.error, 'error_description': exc.error_description}, status_code=exc.status_code, headers=headers)


def _authorization(request):
    values = request.headers.getlist('authorization')
    if len(values) > 1:
        raise OAuthError('invalid_request', 'Multiple Authorization headers are not allowed')
    return values[0] if values else None


@router.get('/.well-known/oauth-authorization-server')
def discovery(config=Depends(_enabled)):
    return JSONResponse(authorization_server_metadata(config), headers=_NO_STORE)


@router.get('/.well-known/oauth-protected-resource')
@router.get('/.well-known/oauth-protected-resource/{resource_path:path}')
def resource_discovery(resource_path: str = '', config=Depends(_enabled)):
    from urllib.parse import urlsplit
    canonical_path = urlsplit(config.resource_url).path.strip('/')
    if resource_path and resource_path.rstrip('/') != canonical_path:
        raise HTTPException(404, 'Unknown protected resource')
    return JSONResponse(protected_resource_metadata(config), headers=_NO_STORE)


@router.post('/api/oauth/register')
async def register(request: Request, config=Depends(_enabled), db: Session = Depends(get_db)):
    # Bound unauthenticated registration growth without trusting X-Forwarded-For.
    now = monotonic()
    key = request.client.host if request.client else 'unknown'
    if key not in _registration_windows:
        for stale_key in list(_registration_windows):
            entries = _registration_windows[stale_key]
            if not entries or entries[-1] <= now - 60:
                del _registration_windows[stale_key]
        while len(_registration_windows) >= 1024:
            del _registration_windows[next(iter(_registration_windows))]
    window = _registration_windows[key]
    while window and window[0] <= now - 60:
        window.popleft()
    if len(window) >= 30:
        return JSONResponse({'error': 'temporarily_unavailable', 'error_description': 'Registration rate limit exceeded'}, status_code=429, headers={**_NO_STORE, 'Retry-After': '60'})
    window.append(now)
    try:
        result = _invoke(db, 'register_client', await _body(request))
    except OAuthError as exc:
        return _error(exc)
    return result if isinstance(result, JSONResponse) else JSONResponse(result, status_code=201, headers=_NO_STORE)


@router.get('/api/oauth/authorize')
def authorize(request: Request, config=Depends(_enabled), db: Session = Depends(get_db)):
    entries = list(request.query_params.multi_items())
    if len(dict(entries)) != len(entries):
        return _error(OAuthError('invalid_request', 'Duplicate parameters are not allowed'))
    params = dict(entries)
    try:
        result = MCPOAuthService(db).begin_authorization(params)
    except OAuthError as exc:
        # OAuth errors may only redirect after checking a persisted client's
        # exact callback; unregistered destinations never receive a redirect.
        from app.models.mcp_oauth import MCPOAuthClient
        client = db.get(MCPOAuthClient, params.get('client_id', ''))
        redirect = params.get('redirect_uri')
        if client is None or redirect not in client.redirect_uris:
            return _error(exc)
        parsed = urlsplit(redirect)
        fields = {'error': exc.error, 'error_description': exc.error_description}
        state = params.get('state')
        if state is not None and len(state) <= 4096:
            fields['state'] = state
        query = parsed.query + ('&' if parsed.query else '') + urlencode(fields)
        return RedirectResponse(urlunsplit((parsed.scheme, parsed.netloc, parsed.path, query, '')), status_code=302, headers=_NO_STORE)
    return RedirectResponse(config.frontend_url + '?' + urlencode({'request_id': result}), status_code=302, headers=_NO_STORE)


@router.post('/api/oauth/token')
async def token(request: Request, config=Depends(_enabled), db: Session = Depends(get_db)):
    try:
        result = _invoke(db, 'exchange_token', await _body(request, form=True), authorization=_authorization(request))
    except OAuthError as exc:
        return _error(exc)
    return result if isinstance(result, JSONResponse) else JSONResponse(result, headers=_NO_STORE)


@router.post('/api/oauth/revoke')
async def revoke(request: Request, config=Depends(_enabled), db: Session = Depends(get_db)):
    try:
        result = _invoke(db, 'revoke_token', await _body(request, form=True), authorization=_authorization(request))
    except OAuthError as exc:
        return _error(exc)
    return result if isinstance(result, JSONResponse) else JSONResponse({}, headers=_NO_STORE)


@router.get('/api/oauth/requests/{request_id}')
def consent_details(request_id: str, config=Depends(_enabled), user=Depends(get_current_user), db: Session = Depends(get_db)):
    result = _invoke(db, 'authorization_details', request_id, user.id)
    return result if isinstance(result, JSONResponse) else JSONResponse(result, headers=_NO_STORE)


class ConsentDecision(BaseModel):
    model_config = ConfigDict(extra='forbid')
    request_id: str
    approve: StrictBool


@router.post('/api/oauth/consent')
def consent(body: ConsentDecision, config=Depends(_enabled), user=Depends(get_current_user), db: Session = Depends(get_db)):
    result = _invoke(db, 'consent', body.request_id, user.id, body.approve)
    return result if isinstance(result, JSONResponse) else JSONResponse({'redirect_uri': result}, headers=_NO_STORE)


@router.get('/api/oauth/grants')
def grants(config=Depends(_enabled), user=Depends(get_current_user), db: Session = Depends(get_db)):
    result = _invoke(db, 'list_grants', user.id)
    return result if isinstance(result, JSONResponse) else JSONResponse(result, headers=_NO_STORE)


@router.delete('/api/oauth/grants/{grant_id}')
def revoke_grant(grant_id: str, config=Depends(_enabled), user=Depends(get_current_user), db: Session = Depends(get_db)):
    from uuid import UUID
    try:
        parsed = UUID(grant_id)
    except ValueError:
        raise HTTPException(404, 'Authorization not found')
    result = _invoke(db, 'revoke_grant', parsed, user.id)
    return result if isinstance(result, JSONResponse) else JSONResponse({}, headers=_NO_STORE)
