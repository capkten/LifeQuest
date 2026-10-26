"""One MCP bearer boundary for PAT and resource-bound OAuth access tokens."""
from app.models.user import User
from app.services.mcp_access_token import MCPAccessTokenService
from app.services.mcp_oauth import MCPOAuthService


def authenticate_mcp_bearer(db, raw_token):
    if not isinstance(raw_token, str):
        return None
    if raw_token.startswith('lq_mcp_'):
        user_id = MCPAccessTokenService(db).authenticate(raw_token)
        return user_id if user_id and db.get(User, user_id) is not None else None
    if raw_token.startswith('lq_oa_'):
        return MCPOAuthService(db).authenticate_access_token(raw_token)
    return None
