"""Canonical OAuth public URLs; never inferred from untrusted request headers."""
from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit

from app.config import settings


@dataclass(frozen=True)
class OAuthConfig:
    enabled: bool
    issuer_url: str
    resource_url: str
    frontend_url: str
    allow_loopback: bool = False
    access_seconds: int = 900
    refresh_seconds: int = 30 * 86400
    request_seconds: int = 600
    code_seconds: int = 120

    @property
    def metadata_url(self) -> str:
        path = urlsplit(self.resource_url).path.rstrip('/')
        parsed = urlsplit(self.resource_url)
        return urlunsplit((parsed.scheme, parsed.netloc, '/.well-known/oauth-protected-resource' + path, '', ''))


def _public_url(value: str, *, allow_loopback: bool, origin_only: bool = False) -> str:
    if not value or any(char.isspace() for char in value) or '\\' in value:
        raise ValueError('OAuth public URLs must be explicit absolute HTTPS URLs')
    parsed = urlsplit(value)
    loopback = parsed.hostname in {'localhost', '127.0.0.1', '::1'}
    if not parsed.hostname or parsed.username is not None or parsed.password is not None:
        raise ValueError('OAuth public URLs must not contain credentials')
    if parsed.query or parsed.fragment or (parsed.scheme != 'https' and not (allow_loopback and loopback and parsed.scheme == 'http')):
        raise ValueError('OAuth requires HTTPS (explicit loopback HTTP is development only)')
    if origin_only and parsed.path not in {'', '/'}:
        raise ValueError('MCP_OAUTH_ISSUER_URL must be an origin without a path')
    # Accessing port also validates its syntax/range.
    parsed.port
    return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), parsed.path.rstrip('/'), '', ''))


def get_oauth_config() -> OAuthConfig:
    if not settings.MCP_OAUTH_ENABLED:
        return OAuthConfig(False, '', '', '')
    allow = settings.MCP_OAUTH_ALLOW_LOOPBACK
    issuer = _public_url(settings.MCP_OAUTH_ISSUER_URL, allow_loopback=allow, origin_only=True)
    resource = _public_url(settings.MCP_OAUTH_RESOURCE_URL or issuer + '/mcp/http', allow_loopback=allow)
    frontend = _public_url(settings.MCP_OAUTH_FRONTEND_URL or issuer + '/oauth/authorize', allow_loopback=allow)
    return OAuthConfig(True, issuer, resource, frontend, allow_loopback=allow)


def authorization_server_metadata(config: OAuthConfig) -> dict:
    endpoint = config.issuer_url + '/api/oauth/'
    return {
        'issuer': config.issuer_url,
        'authorization_endpoint': endpoint + 'authorize',
        'token_endpoint': endpoint + 'token',
        'registration_endpoint': endpoint + 'register',
        'revocation_endpoint': endpoint + 'revoke',
        'response_types_supported': ['code'],
        'grant_types_supported': ['authorization_code', 'refresh_token'],
        'code_challenge_methods_supported': ['S256'],
        'token_endpoint_auth_methods_supported': ['none', 'client_secret_post', 'client_secret_basic'],
        'revocation_endpoint_auth_methods_supported': ['none', 'client_secret_post', 'client_secret_basic'],
        'scopes_supported': ['mcp'],
    }


def protected_resource_metadata(config: OAuthConfig) -> dict:
    return {
        'resource': config.resource_url,
        'authorization_servers': [config.issuer_url],
        'scopes_supported': ['mcp'],
        'bearer_methods_supported': ['header'],
        'resource_name': 'LifeQuest MCP',
    }


def bearer_challenge() -> str:
    config = get_oauth_config()
    if not config.enabled:
        return 'Bearer'
    return f'Bearer resource_metadata="{config.metadata_url}", scope="mcp"'
